#!/usr/bin/env python3
"""
Plato CLI - Command line interface for Plato services

This CLI orchestrates the various Plato services:
- Hub Service: Repository and project management
- Sandbox Service: Development environment management
- SDK: Core API communication

The CLI handles user interaction, command routing, and error display,
while delegating business logic to the appropriate services.
"""

import asyncio
import os
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from plato.sdk import Plato
from plato.hub import Hub
from plato.sandbox import Sandbox
from plato.sandbox_sdk import PlatoSandboxSDK
from dotenv import load_dotenv
import platform
import shutil
import subprocess

import json


# Initialize Rich console
console = Console()
app = typer.Typer(
    help="[bold blue]Plato CLI[/bold blue] - Manage Plato environments and simulators."
)

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
    env_name: str = typer.Argument(
        ..., help="Environment name (e.g., 'espocrm', 'doordash')"
    ),
    interface_type: str = typer.Option("browser", help="Interface type"),
    width: int = typer.Option(1920, help="Viewport width"),
    height: int = typer.Option(1080, help="Viewport height"),
    keepalive: bool = typer.Option(False, "--keepalive", help="Disable timeout"),
    alias: Optional[str] = typer.Option(None, help="Job group alias"),
    open_page: bool = typer.Option(False, "--open-page", help="Open page on start"),
):
    """Create a new Plato environment."""

    async def _make():
        sdk = Plato()
        try:
            console.print(f"[cyan]Creating environment '{env_name}'...[/cyan]")

            with console.status(
                "[bold green]Initializing environment...", spinner="dots"
            ):
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
                + (
                    f"[cyan]Alias:[/cyan] [bold]{env.alias}[/bold]\n"
                    if env.alias
                    else ""
                ),
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


# =============================================================================
# HUB COMMANDS - Repository and Project Management
# =============================================================================

hub_app = typer.Typer(
    help="[bold purple]Hub Commands[/bold purple] - Manage simulator repositories."
)
app.add_typer(hub_app, name="hub")


@hub_app.command()
def init(
    sim_name: str = typer.Argument(..., help="New simulator name"),
    description: Optional[str] = typer.Option(None, help="Simulator description"),
    sim_type: str = typer.Option("docker_app", "--sim-type", help="Simulator type"),
    directory: Optional[str] = typer.Option(None, help="Target directory"),
):
    """Initialize a new simulator with repository."""

    async def _init():
        sdk = Plato()
        hub_service = Hub(sdk, console)

        try:
            console.print(f"[cyan]Initializing simulator '{sim_name}'...[/cyan]")

            result = await hub_service.init_simulator(
                sim_name=sim_name,
                description=description,
                sim_type=sim_type,
                directory=directory,
            )

            if result.success:
                success_panel = Panel.fit(
                    f"[green]Simulator '{sim_name}' created successfully![/green]\n"
                    f"[cyan]Directory:[/cyan] [bold]{result.directory}[/bold]\n"
                    f"[cyan]Repository:[/cyan] {result.repo_full_name}\n"
                    f"[cyan]Next step:[/cyan] cd {result.directory} && start developing",
                    title="[bold green]🎉 Initialization Complete[/bold green]",
                    border_style="green",
                )
                console.print(success_panel)
            else:
                console.print(f"[red]❌ {result.error}[/red]")
                raise typer.Exit(1)

        finally:
            await sdk.close()

    handle_async(_init())


@hub_app.command()
def clone(
    sim_name: str = typer.Argument(..., help="Simulator name to clone"),
    directory: Optional[str] = typer.Option(
        None, "--directory", help="Target directory"
    ),
):
    """Clone a simulator repository."""

    async def _clone():
        sdk = Plato()
        hub_service = Hub(sdk, console)

        try:
            console.print(f"[cyan]Looking up simulator '{sim_name}'...[/cyan]")

            result = await hub_service.clone_simulator(sim_name, directory)

            if result.success:
                console.print(
                    f"[green]✅ Successfully cloned {result.repo_full_name}[/green]"
                )
                console.print(f"[cyan]Repository cloned to:[/cyan] {result.directory}")
                console.print(
                    "[cyan]💡 You can now use 'plato hub sandbox' in this directory[/cyan]"
                )
            else:
                console.print(f"[red]❌ {result.error}[/red]")
                if result.error and "Authentication failed" in result.error:
                    console.print("[yellow]🔧 Try running: plato hub login[/yellow]")
                raise typer.Exit(1)

        finally:
            await sdk.close()

    handle_async(_clone())


@hub_app.command()
def link(
    sim_name: str = typer.Argument(..., help="Simulator name to link"),
    directory: Optional[str] = typer.Option(
        None, help="Directory to link (default: current)"
    ),
):
    """Link a local directory to a simulator repository."""

    async def _link():
        sdk = Plato()
        hub_service = Hub(sdk, console)

        try:
            target_dir = directory or os.getcwd()
            console.print(
                f"[cyan]Linking '{target_dir}' to simulator '{sim_name}'...[/cyan]"
            )

            result = await hub_service.link_directory(sim_name, target_dir)

            if result.success:
                console.print(
                    f"[green]✅ Directory linked to {result.repo_full_name}[/green]"
                )
                console.print("[cyan]💡 Run 'plato hub login' to authenticate[/cyan]")
                console.print("[cyan]💡 Use 'plato hub git push/pull' to sync[/cyan]")
            else:
                console.print(f"[red]❌ {result.error}[/red]")
                raise typer.Exit(1)

        finally:
            await sdk.close()

    handle_async(_link())


@hub_app.command()
def login():
    """Authenticate with Plato hub for git operations."""

    async def _login():
        sdk = Plato()
        hub_service = Hub(sdk, console)

        try:
            console.print("[cyan]🔐 Authenticating with Plato hub...[/cyan]")

            result = await hub_service.authenticate()

            if result.success:
                console.print(
                    "[green]✅ Successfully authenticated with Plato hub[/green]"
                )
                console.print(f"[cyan]👤 Username:[/cyan] {result.username}")
                console.print(f"[cyan]🏢 Organization:[/cyan] {result.org_name}")
                console.print(
                    "[cyan]💡 Credentials cached securely for git operations[/cyan]"
                )
            else:
                console.print(f"[red]❌ Authentication failed: {result.error}[/red]")
                raise typer.Exit(1)

        finally:
            await sdk.close()

    handle_async(_login())


@hub_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def git(ctx: typer.Context):
    """Execute git commands with authenticated Plato hub remote."""

    async def _git():
        sdk = Plato()
        hub_service = Hub(sdk)

        try:
            args = list(ctx.args)
            if not args:
                console.print("[red]❌ Please provide a git command[/red]")
                console.print("[yellow]💡 Example: plato hub git status[/yellow]")
                return

            result = await hub_service.execute_git_command(args)

            if not result.success:
                console.print(f"[red]❌ Git command failed: {result.error}[/red]")
                raise typer.Exit(result.exit_code or 1)

        finally:
            await sdk.close()

    handle_async(_git())


@hub_app.command()
def guide():
    """Complete guide to Plato sandboxing and development workflow."""

    guide_content = """
[bold blue]🚀 Plato Sandbox Development Guide[/bold blue]

[bold cyan]═══ What is Plato Sandboxing? ═══[/bold cyan]

Plato sandboxes let you create [bold]simulations[/bold] of your applications. The goal is to:
1. Get your app running in a cloud environment
2. Start Plato listeners to track mutations (database changes, file changes)
3. Create snapshots that capture your app's behavior
4. [bold green]Voilà! You have a simulation[/bold green] that can replay interactions

[bold cyan]═══ The Simulation Creation Process ═══[/bold cyan]

[bold yellow]Step 1: Get Your App Running[/bold yellow]
   Option A: [dim]ssh plato-sandbox-<vm-id>[/dim] → Connect directly and start manually
   Option B: Use menu [bold]1[/bold] → Start Services (launches docker-compose.yml)

[bold yellow]Step 2: Start Mutation Tracking[/bold yellow]
   Use menu [bold]2[/bold] → Start Listeners (Plato worker monitors your app)

[bold yellow]Step 3: Create Your Simulation[/bold yellow]
   Use menu [bold]4[/bold] → Create VM snapshot
   [bold green]🎉 Your simulation is ready![/bold green]

[bold cyan]═══ Quick Start Workflow ═══[/bold cyan]

[bold yellow]1. Setup[/bold yellow]
   plato hub link <simulator-name>
   plato hub login
   plato hub sandbox

[bold yellow]2. Interactive Menu[/bold yellow]
   ┌────────────────────────────────────────┐
   │ 1 → Start Services     (your app)     │
   │ 2 → Start Listeners    (track changes)│
   │ 3 → Check Services Health             │
   │ 5 → Check Listeners Health            │
   │ 4 → Create Snapshot    (make sim!)    │
   │ 7 → Backup state      8 → Reset state │
   └────────────────────────────────────────┘

[bold cyan]═══ Understanding the Components ═══[/bold cyan]

[bold green]🔧 Your Application Environment[/bold green]
  • Cloud VM with your code at /opt/plato
  • Services can be Docker Compose, standalone apps, or anything else
  • Start via Services menu OR direct SSH access

[bold green]🎧 Plato Listeners (The Magic)[/bold green]
  • Monitors database mutations (INSERT, UPDATE, DELETE)
  • Tracks file system changes
  • [bold]This mutation data becomes your simulation![/bold]

[bold green]📸 Snapshots = Simulations[/bold green]
  • Captures current state + recorded mutations
  • Can be deployed and replayed elsewhere
  • Your app's behavior becomes reusable

[bold cyan]═══ Two Ways to Start Your App ═══[/bold cyan]

[bold yellow]Method 1: Services Menu (Easy)[/bold yellow]
   Choose [bold]1[/bold] → Runs your configured services (Docker Compose, etc.)

[bold yellow]Method 2: Direct SSH (Manual)[/bold yellow]
   [dim]ssh plato-sandbox-<vm-id>[/dim] → Connect directly
   [dim]cd /opt/plato && docker compose up[/dim] → Start manually
   [dim]npm start, python app.py, etc.[/dim] → Start any way you want

[bold cyan]═══ Health Checks ═══[/bold cyan]

Verify everything is working before snapshotting:
• [bold]3[/bold] → Check Services Health (is your app running?)
• [bold]5[/bold] → Check Listeners Health (is Plato tracking mutations?)

Status meanings:
• [bold green]healthy[/bold green] - Ready to create simulation!
• [bold yellow]starting[/bold yellow] - Still booting up
• [bold red]unhealthy/failed[/bold red] - Fix issues before snapshotting

[bold cyan]═══ The End Result ═══[/bold cyan]

After snapshotting, you have:
✅ A [bold]simulation[/bold] that captures your app's behavior
✅ Can be deployed to reproduce interactions
✅ Database changes and file mutations are recorded
✅ Ready for testing, demos, or production use

[bold cyan]═══ Pro Tips ═══[/bold cyan]

• Test your app thoroughly [bold]before[/bold] snapshotting
• Use health checks to ensure listeners are recording
• Snapshots capture the [bold]current moment[/bold] - make it count!
• You can create multiple snapshots of different states

[bold green]🎯 Goal: App Running → Listeners Recording → Snapshot → Simulation Ready![/bold green]
"""

    console.print(guide_content)


# =============================================================================
# PROXYTUNNEL INSTALLER
# =============================================================================


def _is_command_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _install_proxytunnel_noninteractive() -> bool:
    """Attempt to install proxytunnel using the platform's package manager.

    Returns True on success, False otherwise. Avoids interactive prompts.
    """
    try:
        if _is_command_available("proxytunnel"):
            console.print("[green]✅ proxytunnel is already installed[/green]")
            return True

        system = platform.system().lower()

        if system == "darwin":
            # macOS: prefer Homebrew
            if _is_command_available("brew"):
                console.print("[cyan]🔧 Installing proxytunnel via Homebrew...[/cyan]")
                env = os.environ.copy()
                env["NONINTERACTIVE"] = "1"
                # Try list first to skip reinstall
                list_res = subprocess.run(
                    ["brew", "list", "proxytunnel"], capture_output=True, text=True
                )
                if list_res.returncode != 0:
                    res = subprocess.run(
                        ["brew", "install", "proxytunnel"],
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    if res.returncode != 0:
                        console.print(
                            f"[red]❌ Homebrew install failed:[/red] {res.stderr.strip()}"
                        )
                        return False
            else:
                console.print(
                    "[yellow]⚠️  Homebrew not found. Install Homebrew or install proxytunnel manually.[/yellow]"
                )
                console.print(
                    "[cyan]💡 See: https://brew.sh then run: brew install proxytunnel[/cyan]"
                )
                return False

        elif system == "linux":
            console.print(
                "[cyan]🔧 Installing proxytunnel via system package manager...[/cyan]"
            )
            # Try common package managers, preferring non-interactive with sudo -n
            if _is_command_available("apt-get"):
                cmd = [
                    "sudo",
                    "-n",
                    "bash",
                    "-lc",
                    "apt-get update && apt-get install -y proxytunnel",
                ]
            elif _is_command_available("dnf"):
                cmd = ["sudo", "-n", "dnf", "install", "-y", "proxytunnel"]
            elif _is_command_available("yum"):
                cmd = ["sudo", "-n", "yum", "install", "-y", "proxytunnel"]
            elif _is_command_available("pacman"):
                cmd = ["sudo", "-n", "pacman", "-Sy", "--noconfirm", "proxytunnel"]
            elif _is_command_available("apk"):
                cmd = ["sudo", "-n", "apk", "add", "--no-cache", "proxytunnel"]
            else:
                console.print(
                    "[yellow]⚠️  Unsupported Linux distro: please install 'proxytunnel' via your package manager.[/yellow]"
                )
                return False

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                # If sudo -n failed, advise user to re-run with privileges
                hint = " (tip: re-run with sudo)" if "sudo" in cmd[0:1] else ""
                console.print(
                    f"[red]❌ Installation failed:{hint}[/red] {res.stderr.strip() or res.stdout.strip()}"
                )
                return False

        else:
            console.print(
                f"[yellow]⚠️  Unsupported platform '{system}'. Install proxytunnel manually.[/yellow]"
            )
            return False

        # Verify installation
        if not _is_command_available("proxytunnel"):
            console.print(
                "[red]❌ proxytunnel not found in PATH after installation[/red]"
            )
            return False

        # Quick sanity check
        check = subprocess.run(["proxytunnel", "-h"], capture_output=True, text=True)
        if check.returncode not in (0, 1):  # -h may exit 1 depending on build
            console.print(
                f"[yellow]⚠️  proxytunnel installed but health check returned {check.returncode}[/yellow]"
            )
        console.print("[green]✅ proxytunnel installed successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]❌ Failed to install proxytunnel: {e}[/red]")
        return False


@hub_app.command()
def sandbox(
    config: str = typer.Option(
        "plato-config.yml", "--config", help="VM configuration file"
    ),
    dataset: str = typer.Option("base", "--dataset", help="Dataset to use"),
):
    """Start a development sandbox environment."""

    async def _sandbox():
        sdk = Plato()
        sandbox_sdk = PlatoSandboxSDK()
        try:
            # Best-effort: ensure proxytunnel is available locally
            try:
                console.print("[dim]🔧 Ensuring proxytunnel is installed...[/dim]")
                _install_proxytunnel_noninteractive()
            except Exception as _e:
                console.print(
                    "[red]❌ Could not install proxytunnel automatically; continuing.[/red]"
                )

            # Initialize sandbox service (async init) with a live progress spinner
            sandbox_service = Sandbox()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Provisioning sandbox (VM, SSH, tunnel)...", total=None
                )
                await sandbox_service.init(console, dataset, sdk, sandbox_sdk)
                progress.update(task, description="[green]Sandbox ready[/green]")

            # Run interactive sandbox menu
            try:
                await run_interactive_sandbox_menu(sandbox_service)
            except (KeyboardInterrupt, typer.Abort, EOFError, asyncio.CancelledError):
                # Graceful exit: don't propagate, cleanup in finally
                return

        except Exception as e:
            # Only report real errors; ignore cancellation
            if not isinstance(
                e, (KeyboardInterrupt, typer.Abort, EOFError, asyncio.CancelledError)
            ):
                console.print(f"[red]❌ Sandbox failed: {e}[/red]")
                raise typer.Exit(1)
        finally:
            try:
                import signal as _signal

                _prev_sig = _signal.getsignal(_signal.SIGINT)
                try:
                    _signal.signal(_signal.SIGINT, _signal.SIG_IGN)
                    await asyncio.shield(sandbox_service.close())
                finally:
                    try:
                        _signal.signal(_signal.SIGINT, _prev_sig)
                    except Exception:
                        pass
            except (Exception, KeyboardInterrupt, asyncio.CancelledError):
                pass
            try:
                import signal as _signal

                _prev_sig2 = _signal.getsignal(_signal.SIGINT)
                try:
                    _signal.signal(_signal.SIGINT, _signal.SIG_IGN)
                    await asyncio.shield(sdk.close())
                finally:
                    try:
                        _signal.signal(_signal.SIGINT, _prev_sig2)
                    except Exception:
                        pass
            except (Exception, KeyboardInterrupt, asyncio.CancelledError):
                pass

    handle_async(_sandbox())


async def run_interactive_sandbox_menu(sandbox: Sandbox):
    """Interactive sandbox menu - handles all user interaction."""

    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    console.print(
        Panel.fit(
            "[bold green]Sandbox is ready![/bold green] Choose an action:",
            title="[bold blue]🚀 Interactive Sandbox[/bold blue]",
            border_style="blue",
        )
    )

    while True:
        # Display menu
        menu_table = Table(title="[bold cyan]📋 Sandbox Menu[/bold cyan]")
        menu_table.add_column("Option", style="cyan", no_wrap=True)
        menu_table.add_column("Action", style="white")
        menu_table.add_row("0", "Display Sandbox Info")
        menu_table.add_row("1", "Run Services (submit + health loop)")
        menu_table.add_row("2", "Run Worker (submit + health loop)")
        menu_table.add_row("3", "Sim Backup")
        menu_table.add_row("4", "Sim Reset")
        menu_table.add_row("5", "Create VM snapshot")

        console.print("\n")
        console.print(menu_table)

        try:
            raw = input("Choose an action (0-5 or q to quit): ")
        except KeyboardInterrupt:
            return
        except EOFError:
            return

        raw = (raw or "").strip()
        if not raw:
            continue
        if raw.lower() in {"q", "x", "quit", "exit"}:
            break
        try:
            choice = int(raw)
        except ValueError:
            console.print("[red]❌ Invalid choice. Please enter a number.[/red]")
            continue

        if choice == 0:
            await handle_display_sandbox_info(sandbox)
        elif choice == 1:
            await handle_run_services(sandbox)
        elif choice == 2:
            await handle_run_worker(sandbox)
        elif choice == 3:
            await handle_sim_backup(sandbox)
        elif choice == 4:
            await handle_sim_reset(sandbox)
        elif choice == 5:
            await handle_create_snapshot(sandbox)
        else:
            console.print("[red]❌ Invalid choice. Please enter 0-5.[/red]")


async def handle_run_all(sandbox: Sandbox):
    # Deprecated; kept for compatibility but directs users to new commands
    console.print(
        "[yellow]⚠️ 'Run All' is deprecated. Use 'Run Services' then 'Run Worker'.[/yellow]"
    )


async def handle_display_sandbox_info(sandbox: Sandbox):
    """Handle displaying sandbox information."""
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    info = sandbox.sandbox_info

    # Create formatted info panel (adapted for platohub SandboxInfo structure)
    info_content = (
        f"[cyan]🔗 SSH Connection:[/cyan]\n"
        f"  [bold green]ssh {info.ssh_host}[/bold green]\n\n"
        f"[cyan]🌐 VM URL:[/cyan]\n"
        f"  [blue]{info.url}[/blue]\n\n"
        f"[cyan]🔌 SSH URL:[/cyan]\n"
        f"  [blue]{info.ssh_url}[/blue]\n\n"
        f"[cyan]🔧 Service:[/cyan]\n"
        f"  [bold]{info.service}[/bold]\n\n"
        f"[cyan]📊 Dataset:[/cyan]\n"
        f"  [bold]{info.dataset}[/bold]\n\n"
        f"[cyan]🔑 Public ID:[/cyan]\n"
        f"  [dim]{info.public_id}[/dim]\n\n"
        f"[cyan]🏷️  Job Group ID:[/cyan]\n"
        f"  [dim]{info.job_group_id}[/dim]\n\n"
        f"[cyan]💾 Commit Hash:[/cyan]\n"
        f"  [dim]{info.commit_hash[:12]}...[/dim]\n\n"
        f"[cyan]🔌 Local Port:[/cyan]\n"
        f"  [bold]{info.local_port}[/bold]"
    )

    info_panel = Panel.fit(
        info_content,
        title="[bold blue]📋 Sandbox Information[/bold blue]",
        border_style="blue",
    )
    console.print(info_panel)


async def handle_sim_backup(sandbox: Sandbox):
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    console.print("[cyan]💾 Creating simulator backup...[/cyan]")

    try:
        await sandbox.client.backup_environment(sandbox.sandbox_info.public_id)
    except Exception as e:
        console.print(f"[red]❌ Error creating backup: {e}[/red]")


async def handle_sim_reset(sandbox: Sandbox):
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    console.print("[cyan]🔄 Resetting simulator environment...[/cyan]")

    try:
        await sandbox.client.reset_environment(sandbox.sandbox_info.public_id)
    except Exception as e:
        console.print(f"[red]❌ Error resetting simulator: {e}[/red]")


async def handle_run_services(sandbox: Sandbox):
    """Submit start-services and loop on healthy-services with progress."""
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    # Helper to parse last JSON line from stdout
    def _parse_last_json(stdout: str) -> dict | None:
        if not stdout:
            return None
        for line in reversed(stdout.strip().split("\n")):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "status" in obj:
                    return obj
            except Exception:
                continue
        return None

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Submitting start-services...", total=None)

            submit = await sandbox.sandbox_sdk.start_services(
                public_id=sandbox.sandbox_info.public_id,
                dataset=sandbox.sandbox_info.dataset,
                dataset_config=sandbox.sandbox_info.dataset_config,
            )

            start_result = await sandbox._monitor_ssh_execution_with_data(
                sandbox.client,
                submit.correlation_id,
                "Start Services",
                timeout=900,
            )
            start_obj = _parse_last_json(start_result.stdout or "")
            if (
                not start_result.success
                or not start_obj
                or start_obj.get("status") == "error"
            ):
                progress.update(task, description="[red]Start-services failed[/red]")
                console.print(
                    f"[red]❌ Error starting services: {(start_result.error or (start_obj or {}).get('message') or 'unknown error')}[/red]"
                )
                return
            progress.update(task, description="[green]Start-services submitted[/green]")

            # Poll health until success or timeout
            service_timeout = 900
            max_retries = 60
            delay_s = 5
            attempts = 0
            start_time = asyncio.get_event_loop().time()
            while attempts < max_retries:
                attempts += 1
                progress.update(
                    task, description=f"[cyan]Health check attempt {attempts}...[/cyan]"
                )
                health_submit = await sandbox.sandbox_sdk.healthy_services(
                    public_id=sandbox.sandbox_info.public_id,
                    dataset=sandbox.sandbox_info.dataset,
                    dataset_config=sandbox.sandbox_info.dataset_config,
                )
                health_result = await sandbox._monitor_ssh_execution_with_data(
                    sandbox.client,
                    health_submit.correlation_id,
                    "Services Health",
                    timeout=60,
                )
                obj = _parse_last_json(health_result.stdout or "")
                status = (obj or {}).get("status", "unknown")
                message = (obj or {}).get("message", "")
                progress.update(
                    task, description=f"[cyan]Health: {status} - {message}[/cyan]"
                )
                if status == "success":
                    progress.update(task, description="[green]Services healthy[/green]")
                    console.print("[green]✅ Services are healthy![/green]")
                    return
                if (asyncio.get_event_loop().time() - start_time) > service_timeout:
                    break
                await asyncio.sleep(delay_s)

            progress.update(
                task,
                description="[yellow]Timed out waiting for healthy services[/yellow]",
            )
            console.print(
                "[yellow]⚠️ Services did not become healthy within timeout[/yellow]"
            )

    except KeyboardInterrupt:
        console.print(
            "[yellow]⏹ Cancelled run-services; services may continue starting in the background[/yellow]"
        )
        return
    except Exception as e:
        console.print(f"[red]❌ Error running services: {e}[/red]")


async def handle_run_worker(sandbox: Sandbox):
    """Submit start-worker and loop on healthy-worker with progress."""
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    # Helper to parse last JSON line from stdout
    def _parse_last_json(stdout: str) -> dict | None:
        if not stdout:
            return None
        for line in reversed(stdout.strip().split("\n")):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "status" in obj:
                    return obj
            except Exception:
                continue
        return None

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Submitting start-worker...", total=None)

            submit = await sandbox.sandbox_sdk.start_worker(
                public_id=sandbox.sandbox_info.public_id,
                dataset=sandbox.sandbox_info.dataset,
                dataset_config=sandbox.sandbox_info.dataset_config,
            )
            start_result = await sandbox._monitor_ssh_execution_with_data(
                sandbox.client,
                submit.correlation_id,
                "Start Worker",
                timeout=600,
            )
            start_obj = _parse_last_json(start_result.stdout or "")
            if (
                not start_result.success
                or not start_obj
                or start_obj.get("status") == "error"
            ):
                progress.update(task, description="[red]Start-worker failed[/red]")
                console.print(
                    f"[red]❌ Error starting worker: {(start_result.error or (start_obj or {}).get('message') or 'unknown error')}[/red]"
                )
                return
            progress.update(task, description="[green]Start-worker submitted[/green]")

            # Poll worker health until success or timeout
            worker_timeout = 600
            max_retries = 60
            delay_s = 5
            attempts = 0
            start_time = asyncio.get_event_loop().time()
            while attempts < max_retries:
                attempts += 1
                progress.update(
                    task,
                    description=f"[cyan]Worker health attempt {attempts}...[/cyan]",
                )
                submit_h = await sandbox.sandbox_sdk.healthy_worker(
                    public_id=sandbox.sandbox_info.public_id
                )
                result_h = await sandbox._monitor_ssh_execution_with_data(
                    sandbox.client,
                    submit_h.correlation_id,
                    "Worker Health",
                    timeout=60,
                )
                obj = _parse_last_json(result_h.stdout or "")

                # Better error handling for parsing
                if obj:
                    status = obj.get("status", "unknown")
                    message = obj.get("message", "")
                else:
                    # If parsing failed, show raw output for debugging
                    status = "parse_error"
                    message = f"Could not parse: {(result_h.stdout or '')[:100]}"

                # Clean up the message (remove any trailing newlines/unknowns)
                message = message.strip()

                progress.update(task, description=f"[cyan]Worker: {message}[/cyan]")
                if status == "success":
                    progress.update(task, description="[green]Worker healthy[/green]")
                    console.print("[green]✅ Worker is healthy![/green]")
                    return
                if (asyncio.get_event_loop().time() - start_time) > worker_timeout:
                    break
                await asyncio.sleep(delay_s)

            progress.update(
                task,
                description="[yellow]Timed out waiting for healthy worker[/yellow]",
            )
            console.print(
                "[yellow]⚠️ Worker did not become healthy within timeout[/yellow]"
            )

    except KeyboardInterrupt:
        console.print(
            "[yellow]⏹ Cancelled run-worker; worker may continue starting in the background[/yellow]"
        )
        return
    except Exception as e:
        console.print(f"[red]❌ Error running worker: {e}[/red]")


async def handle_create_snapshot(sandbox: Sandbox):
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Submitting snapshot request...", total=None)

            # Submit snapshot request
            submit = await sandbox.sandbox_sdk.snapshot(sandbox.sandbox_info.public_id)

            # Monitor snapshot creation
            progress.update(task, description="[cyan]Creating VM snapshot...[/cyan]")
            result = await sandbox._monitor_ssh_execution_with_data(
                sandbox.client,
                submit.correlation_id,
                "VM Snapshot",
                timeout=1800,  # 30 minutes for snapshot creation
            )

            if result.success:
                progress.update(
                    task, description="[green]Snapshot created successfully![/green]"
                )
                console.print("[green]✅ VM snapshot created successfully![/green]")
                if result.snapshot_s3_uri:
                    console.print(f"[cyan]📦 S3 URI: {result.snapshot_s3_uri}[/cyan]")
                if result.snapshot_dir:
                    console.print(
                        f"[cyan]📁 Snapshot directory: {result.snapshot_dir}[/cyan]"
                    )
            else:
                progress.update(task, description="[red]Snapshot failed[/red]")
                error_msg = result.error or "Unknown error"
                console.print(f"[red]❌ Error creating snapshot: {error_msg}[/red]")
                if result.stderr:
                    console.print(f"[red]📤 Error details: {result.stderr}[/red]")
                console.print(
                    "[yellow]💡 Tip: Snapshots work best after services are running. Try starting services first.[/yellow]"
                )

    except Exception as e:
        console.print(f"[red]❌ Error creating snapshot: {e}[/red]")


def main():
    """Main entry point for the Plato CLI."""
    app()


# Backward compatibility
cli = main

if __name__ == "__main__":
    main()
