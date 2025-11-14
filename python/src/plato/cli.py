import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path

import typer
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from plato.sdk import Plato

# Initialize Rich console
console = Console()
app = typer.Typer(
    help="[bold blue]Plato CLI[/bold blue] - Manage Plato environments and simulators."
)

# Set up Rich logging handler for FlowExecutor
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_time=False, show_path=False)],
)
flow_logger = logging.getLogger("plato.flow")


def _find_bundled_cli() -> str | None:
    """
    Find the bundled Plato CLI binary.

    Returns:
        Path to the bundled CLI binary if found, None otherwise.
    """
    # Determine the expected binary name
    binary_name = "plato-cli.exe" if platform.system().lower() == "windows" else "plato-cli"

    # Look for the binary in the package's bin directory
    # This file (__file__) is at src/plato/cli.py, so bin is at src/plato/bin/
    package_dir = Path(__file__).resolve().parent
    bin_dir = package_dir / "bin"
    binary_path = bin_dir / binary_name

    if binary_path.exists() and os.access(binary_path, os.X_OK):
        return str(binary_path)

    return None


# Load environment variables
load_dotenv()
load_dotenv(dotenv_path=os.path.join(os.path.expanduser("~"), ".env"))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def handle_async(coro):
    """Helper to run async functions with proper error handling."""
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        console.print("\n[red]🛑 Operation cancelled by user.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if "401" in str(e) or "Unauthorized" in str(e):
            console.print(
                "💡 [yellow]Hint: Make sure PLATO_API_KEY is set in your environment[/yellow]"
            )
        raise typer.Exit(1)


# =============================================================================
# ENVIRONMENT COMMANDS
# =============================================================================


@app.command()
def make(
    env_name: str = typer.Argument(..., help="Environment name (e.g., 'espocrm', 'doordash')"),
    interface_type: str = typer.Option("browser", help="Interface type"),
    width: int = typer.Option(1920, help="Viewport width"),
    height: int = typer.Option(1080, help="Viewport height"),
    keepalive: bool = typer.Option(False, "--keepalive", help="Disable timeout"),
    alias: str | None = typer.Option(None, help="Job group alias"),
    open_page: bool = typer.Option(False, "--open-page", help="Open page on start"),
):
    """Create a new Plato environment."""

    async def _make():
        sdk = Plato()
        try:
            console.print(f"[cyan]Creating environment '{env_name}'...[/cyan]")

            with console.status("[bold green]Initializing environment...", spinner="dots"):
                env = await sdk.make_environment(
                    env_id=env_name,
                    interface_type="browser",
                    viewport_width=width,
                    viewport_height=height,
                    keepalive=keepalive,
                    alias=alias,
                    open_page_on_start=open_page,
                )

            # Display success
            success_panel = Panel.fit(
                f"[green]Environment created successfully![/green]\n"
                f"[cyan]Environment ID:[/cyan] [bold]{env.id}[/bold]\n"
                + (f"[cyan]Alias:[/cyan] [bold]{env.alias}[/bold]\n" if env.alias else ""),
                title="[bold green]✅ Success[/bold green]",
                border_style="green",
            )
            console.print(success_panel)

            # Wait for ready with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Waiting for environment...", total=None)
                await env.wait_for_ready(timeout=300.0)
                progress.update(task, description="[green]Environment ready!")

            # Get and display public URL
            try:
                public_url = await env.get_public_url()
                url_panel = Panel.fit(
                    f"[blue]{public_url}[/blue]",
                    title="[bold blue]🌐 Public URL[/bold blue]",
                    border_style="blue",
                )
                console.print(url_panel)
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not get public URL: {e}[/yellow]")

        finally:
            await sdk.close()

    handle_async(_make())


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def hub(
    ctx: typer.Context,
):
    """
    Launch the Plato Hub CLI (interactive TUI for managing simulators).

    The hub command opens the Go-based Plato CLI which provides an interactive
    terminal UI for browsing simulators, launching environments, and managing VMs.

    Available subcommands:
    - clone <service>: Clone a service from Plato Hub
    - credentials: Display your Plato Hub credentials
    - (no args): Start interactive TUI mode

    Examples:
        plato hub clone espocrm
        plato hub credentials
        plato hub
    """
    # Find the bundled CLI binary
    plato_bin = _find_bundled_cli()

    if not plato_bin:
        console.print("[red]❌ Plato CLI binary not found in package[/red]")
        console.print(
            "\n[yellow]The bundled CLI binary was not found in this installation.[/yellow]"
        )
        console.print("This indicates an installation issue with the plato-sdk package.")
        console.print("\n[yellow]💡 Try reinstalling the package:[/yellow]")
        console.print("   pip install --upgrade --force-reinstall plato-sdk")
        console.print("\n[dim]If the issue persists, please report it at:[/dim]")
        console.print("[dim]https://github.com/plato-app/plato-client/issues[/dim]")
        raise typer.Exit(1)

    # Get any additional arguments passed after 'hub'
    args = ctx.args if hasattr(ctx, "args") else []

    try:
        # Launch the Go CLI, passing through all arguments
        # Use execvp to replace the current process so the TUI works properly
        os.execvp(plato_bin, [plato_bin] + args)
    except Exception as e:
        console.print(f"[red]❌ Failed to launch Plato Hub: {e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# SYNC COMMAND
# =============================================================================


@app.command()
def sync():
    """
    Sync local code to a remote Plato VM using rsync.

    Reads .sandbox.yaml to get ssh_host and service name.
    Syncs to /home/plato/worktree/<service-name>.

    Example:
        plato sync
    """
    # Check if rsync is available
    if not shutil.which("rsync"):
        console.print("[red]❌ rsync is not installed[/red]")
        console.print("\n[yellow]Please install rsync:[/yellow]")
        console.print("  macOS:   brew install rsync")
        console.print("  Linux:   apt-get install rsync or yum install rsync")
        raise typer.Exit(1)

    # Read .sandbox.yaml
    sandbox_file = Path.cwd() / ".sandbox.yaml"

    if not sandbox_file.exists():
        console.print("[red]❌ .sandbox.yaml not found[/red]")
        console.print("\n[yellow]Create a sandbox with: [bold]plato hub[/bold][/yellow]")
        raise typer.Exit(1)

    try:
        with open(sandbox_file) as f:
            sandbox_data = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]❌ Error reading .sandbox.yaml: {e}[/red]")
        raise typer.Exit(1) from e

    # Get required fields
    ssh_host = sandbox_data.get("ssh_host")
    plato_config_path = sandbox_data.get("plato_config_path")

    if not ssh_host:
        console.print("[red]❌ .sandbox.yaml missing 'ssh_host'[/red]")
        raise typer.Exit(1)

    if not plato_config_path:
        console.print("[red]❌ .sandbox.yaml missing 'plato_config_path'[/red]")
        raise typer.Exit(1)

    # Load plato-config.yml to get service name
    try:
        with open(plato_config_path) as f:
            plato_config = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]❌ Could not read plato-config.yml: {e}[/red]")
        raise typer.Exit(1)

    service = plato_config.get("service")
    if not service:
        console.print("[red]❌ plato-config.yml missing 'service'[/red]")
        raise typer.Exit(1)

    # Build remote path
    remote_path = f"/home/plato/worktree/{service}"

    console.print(f"[cyan]SSH host: {ssh_host}[/cyan]")
    console.print(f"[cyan]Service: {service}[/cyan]")
    console.print(f"[cyan]Remote path: {remote_path}[/cyan]")

    # Build rsync command
    local_path = Path.cwd()

    # Hardcoded excludes
    excludes = [
        "__pycache__",
        "*.pyc",
        ".git",
        ".venv",
        ".sandbox.yaml",
    ]

    cmd = ["rsync", "-avz", "--delete", "--info=progress2"]

    # Add excludes
    for pattern in excludes:
        cmd.extend(["--exclude", pattern])

    # Use SSH with config file
    ssh_config_file = Path.home() / ".ssh" / "config"
    cmd.extend(["-e", f"ssh -F {ssh_config_file}"])

    # Add source and destination
    source = str(local_path) + "/"
    destination = f"{ssh_host}:{remote_path}/"
    cmd.extend([source, destination])

    # Display info
    console.print(f"\n[bold]Syncing {local_path} to {ssh_host}:{remote_path}[/bold]\n")

    # Execute rsync
    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            console.print(f"\n[green]✓ Successfully synced to {ssh_host}[/green]")
        else:
            console.print(f"\n[red]✗ Sync failed with exit code {result.returncode}[/red]")
            raise typer.Exit(result.returncode)
    except KeyboardInterrupt:
        console.print("\n[yellow]Sync interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]❌ Error running rsync: {e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# ENV-REVIEW COMMAND
# =============================================================================


@app.command()
def review():
    """
    Review a Plato environment with an artifact ID.

    Prompts for simulator name and artifact ID.

    Example:
        plato review
    """
    console.print("[bold cyan]🚀 Plato Environment Review[/bold cyan]")
    console.print("=" * 40)

    # Get API key
    api_key = os.getenv("PLATO_API_KEY")
    if not api_key:
        console.print("[yellow]📝 API Key not found in environment.[/yellow]")
        api_key = typer.prompt("Enter your Plato API key", hide_input=True)
    else:
        console.print("[green]✅ Using API key from environment[/green]")

    # Get artifact ID
    artifact_id = typer.prompt("\n📦 Enter artifact ID").strip()
    if not artifact_id:
        console.print("[red]❌ Error: Artifact ID is required[/red]")
        raise typer.Exit(1)

    # Get simulator name
    simulator = typer.prompt("🖥️  Enter simulator name").strip()
    if not simulator:
        console.print("[red]❌ Error: Simulator name is required[/red]")
        raise typer.Exit(1)

    console.print()
    console.print(
        f"[cyan]🚀 Creating {simulator} environment with artifact ID: {artifact_id}[/cyan]"
    )
    console.print("[cyan]🌍 Using production environment: https://plato.so/api[/cyan]")

    async def _spin_up_environment():
        base_url = "https://plato.so/api"
        client = Plato(base_url=base_url, api_key=api_key)
        environment = None
        playwright = None
        browser = None
        page = None

        try:
            # Create the environment
            console.print("[cyan]📦 Creating environment...[/cyan]")
            environment = await client.make_environment(simulator, artifact_id=artifact_id)
            console.print(f"[green]✅ Environment created with ID: {environment.id}[/green]")

            # Wait for the environment to be ready
            console.print(
                "[cyan]⏳ Waiting for environment to be ready (timeout: 2 minutes)...[/cyan]"
            )
            await environment.wait_for_ready(timeout=120.0)
            console.print("[green]✅ Environment is ready![/green]")

            # Reset the environment
            console.print("[cyan]🔄 Resetting environment to clean state...[/cyan]")
            await environment.reset()
            console.print("[green]✅ Environment reset complete![/green]")

            # Get the public URL
            console.print("[cyan]🔗 Fetching public URL...[/cyan]")
            public_url = await environment.get_public_url()

            # Display success information
            console.print("\n" + "=" * 80)
            console.print("[bold green]🎉 ENVIRONMENT READY![/bold green]")
            console.print("=" * 80)
            console.print(f"[cyan]Simulator:[/cyan]      {simulator}")
            console.print(f"[cyan]Artifact ID:[/cyan]    {artifact_id}")
            console.print(f"[cyan]Environment ID:[/cyan] {environment.id}")
            console.print(f"[cyan]Public URL:[/cyan]     {public_url}")
            console.print("=" * 80)
            console.print()

            # Optionally spin up a Playwright browser
            try:
                from playwright.async_api import async_playwright

                console.print(
                    "[cyan]🧭 Launching Playwright browser for environment login...[/cyan]"
                )
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(public_url)
                try:
                    await environment.login(page, from_api=True, throw_on_login_error=True)
                    console.print(
                        "[green]✅ Successfully logged into environment via Playwright[/green]"
                    )
                except Exception as e:
                    console.print(f"[red]❌ Error during Playwright env.login: {e}[/red]")
            except ImportError:
                console.print(
                    "[yellow]⚠️  Playwright is not installed; skipping browser launch[/yellow]"
                )
            except Exception as e:
                console.print(f"[red]❌ Failed to start Playwright browser: {e}[/red]")

            # Interactive loop
            console.print(
                "[cyan]🔗 Environment is running and accessible via the public URL above.[/cyan]"
            )
            console.print("\n[bold]📋 Available commands:[/bold]")
            console.print("  - 'state' or 's': Get current environment state")
            console.print("  - 'end' or 'e': Shut down the environment")
            console.print()

            while True:
                try:
                    command = input("Enter command: ").strip().lower()

                    if command in ["end", "e"]:
                        console.print("[yellow]👋 Shutting down environment...[/yellow]")
                        break
                    elif command in ["state", "s"]:
                        console.print("\n[cyan]🔍 Getting environment state...[/cyan]")
                        try:
                            state = await environment.get_state()
                            console.print("\n[bold]📊 Current Environment State:[/bold]")
                            console.print("-" * 40)
                            if isinstance(state, dict):
                                console.print(json.dumps(state, indent=2))
                            else:
                                console.print(state)
                            console.print("-" * 40)
                            console.print()
                        except Exception as e:
                            console.print(f"[red]❌ Error getting state: {e}[/red]")
                    else:
                        console.print("[yellow]❓ Unknown command. Use 'state' or 'end'[/yellow]")

                except KeyboardInterrupt:
                    console.print("\n[yellow]⚠️  Interrupted! Shutting down environment...[/yellow]")
                    break

        except Exception as e:
            console.print(f"[red]❌ Error creating or managing environment: {e}[/red]")
            raise

        finally:
            # Clean up the Playwright browser
            try:
                if page is not None:
                    await page.close()
                if browser is not None:
                    await browser.close()
                if playwright is not None:
                    await playwright.stop()
            except Exception as e:
                console.print(f"[yellow]⚠️  Error during Playwright cleanup: {e}[/yellow]")

            # Clean up the environment
            if environment:
                try:
                    console.print("[cyan]🧹 Shutting down environment...[/cyan]")
                    await environment.close()
                    console.print("[green]✅ Environment shut down successfully[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️  Error during cleanup: {e}[/yellow]")

            # Close the client
            try:
                await client.close()
                console.print("[green]✅ Client closed[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Error closing client: {e}[/yellow]")

    handle_async(_spin_up_environment())


@app.command()
def flow(
    flow_name: str = typer.Option("login", "--flow-name", "-f", help="Name of the flow to execute"),
):
    """
    Execute a test flow against a simulator environment.

    Reads .sandbox.yaml to get the URL. Auto-detects flow file
    (flows.yaml, flows.yml, flow.yaml, flow.yml). Uses "login" as default flow name.

    Example:
        plato run-flow
    """
    from playwright.async_api import async_playwright

    from plato.flow_executor import FlowExecutor
    from plato.models.flow import Flow

    sandbox_file = Path.cwd() / ".sandbox.yaml"
    if not sandbox_file.exists():
        console.print("[red]❌ .sandbox.yaml not found[/red]")
        console.print("\n[yellow]Create a sandbox with: [bold]plato hub[/bold][/yellow]")
        raise typer.Exit(1)
    try:
        with open(sandbox_file) as f:
            sandbox_data = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]❌ Error reading .sandbox.yaml: {e}[/red]")
        raise typer.Exit(1) from e

    url = sandbox_data.get("url")
    dataset = sandbox_data.get("dataset")
    if not url:
        console.print("[red]❌ .sandbox.yaml missing 'url'[/red]")
        raise typer.Exit(1)
    if not dataset:
        console.print("[red]❌ .sandbox.yaml missing 'dataset'[/red]")
        raise typer.Exit(1)

    plato_config_path = sandbox_data.get("plato_config_path")
    if not plato_config_path:
        console.print("[red]❌ .sandbox.yaml missing 'plato_config_path'[/red]")
        raise typer.Exit(1)
    try:
        with open(plato_config_path) as f:
            plato_config = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]❌ Could not read plato-config.yml: {e}[/red]")
        raise typer.Exit(1) from e

    flow_file = None
    if dataset and "datasets" in plato_config:
        dataset_config = plato_config["datasets"].get(dataset, {})
        metadata = dataset_config.get("metadata", {})
        flows_path = metadata.get("flows_path")

        if flows_path:
            if not Path(flows_path).is_absolute():
                config_dir = Path(plato_config_path).parent
                flow_file = str(config_dir / flows_path)
            else:
                flow_file = flows_path
    if not flow_file or not Path(flow_file).exists():
        console.print("[red]❌ Flow file not found in plato-config[/red]")
        console.print(
            f"[yellow]Dataset '{dataset}' missing metadata.flows_path in plato-config.yml[/yellow]"
        )
        raise typer.Exit(1)
    with open(flow_file) as f:
        flow_dict = yaml.safe_load(f)

    console.print(f"[cyan]Flow file: {flow_file}[/cyan]")
    console.print(f"[cyan]URL: {url}[/cyan]")
    console.print(f"[cyan]Flow name: {flow_name}[/cyan]")

    flow = next(
        (
            Flow.model_validate(flow)
            for flow in flow_dict.get("flows", [])
            if flow.get("name") == flow_name
        ),
        None,
    )
    if not flow:
        console.print(f"[red]❌ Flow named '{flow_name}' not found in {flow_file}[/red]")
        raise typer.Exit(1)

    screenshots_dir = Path(flow_file).parent / "screenshots"

    async def _run():
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(url)
                executor = FlowExecutor(page, flow, screenshots_dir, logger=flow_logger)
                result = await executor.execute_flow()
                console.print("[green]✅ Flow executed successfully[/green]")
                return result
        except Exception as e:
            console.print(f"[red]❌ Flow execution failed: {e}[/red]")
            raise typer.Exit(1) from e
        finally:
            if browser:
                await browser.close()

    handle_async(_run())


@app.command()
def state():
    """Get the current state of the simulator environment (reads .sandbox.yaml)."""
    # Read .sandbox.yaml
    sandbox_file = Path.cwd() / ".sandbox.yaml"
    if not sandbox_file.exists():
        console.print("[red]❌ No .sandbox.yaml - run: plato hub[/red]")
        raise typer.Exit(1)

    with open(sandbox_file) as f:
        data = yaml.safe_load(f)

    job_group_id = data.get("job_group_id")
    if not job_group_id:
        console.print("[red]❌ .sandbox.yaml missing job_group_id[/red]")
        raise typer.Exit(1)

    # Get API key
    api_key = os.getenv("PLATO_API_KEY")
    if not api_key:
        console.print("[red]❌ PLATO_API_KEY not set[/red]")
        raise typer.Exit(1)

    async def _get_state():
        client = Plato(api_key=api_key)
        try:
            console.print(f"[cyan]Getting state for job_group_id: {job_group_id}[/cyan]")
            state = await client.get_environment_state(job_group_id, merge_mutations=False)

            console.print("\n[bold]Environment State:[/bold]")
            console.print(json.dumps(state, indent=2))
        finally:
            await client.close()

    handle_async(_get_state())


@app.command()
def audit_ui():
    """
    Launch Streamlit UI for auditing database ignore rules.

    Note: Requires streamlit to be installed:
        pip install streamlit psycopg2-binary pymysql

    Examples:
        plato audit-ui
    """
    # Check if streamlit is installed
    if not shutil.which("streamlit"):
        console.print("[red]❌ streamlit is not installed[/red]")
        console.print("\n[yellow]Install with:[/yellow]")
        console.print("  pip install streamlit psycopg2-binary pymysql")
        raise typer.Exit(1)

    # Find the audit_ui.py file
    package_dir = Path(__file__).resolve().parent
    ui_file = package_dir / "audit_ui.py"

    if not ui_file.exists():
        console.print(f"[red]❌ UI file not found: {ui_file}[/red]")
        raise typer.Exit(1)

    console.print("[cyan]Launching Streamlit UI...[/cyan]")

    try:
        # Launch streamlit
        os.execvp("streamlit", ["streamlit", "run", str(ui_file)])
    except Exception as e:
        console.print(f"[red]❌ Failed to launch Streamlit: {e}[/red]")
        raise typer.Exit(1) from e


def main():
    """Main entry point for the Plato CLI."""
    app()


# Backward compatibility
cli = main

if __name__ == "__main__":
    main()
