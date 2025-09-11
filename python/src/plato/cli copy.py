#!/usr/bin/env python3
"""
Plato CLI - Command line interface for Plato SDK
"""

import asyncio
import json

# import sys  # Removed - using typer.Exit instead
import os
import shutil
import tempfile
from typing import Optional, Dict, List, Any, Union

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

# from rich.text import Text  # Reserved for future use
# from rich import print as rprint  # Reserved for future use
from plato.sdk import Plato
from plato.exceptions import PlatoClientError
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal
from core.util.adaptive_object import AdaptiveObject

# Initialize Rich console
console = Console()
app = typer.Typer(
    help="[bold blue]Plato CLI[/bold blue] - Manage Plato environments from the command line."
)


# Pydantic models for plato-config.yml structure
class ComputeConfig(BaseModel):
    """Compute resource configuration for the VM."""

    cpus: int = Field(default=1, ge=1, le=8, description="Number of CPU cores")
    memory: int = Field(default=2048, ge=512, le=16384, description="Memory in MB")
    disk: int = Field(default=10240, ge=1024, le=102400, description="Disk space in MB")
    app_port: int = Field(
        default=8080, ge=1024, le=65535, description="Application port"
    )
    plato_messaging_port: int = Field(
        default=7000, ge=1024, le=65535, description="Plato messaging port"
    )


class ServiceConfig(AdaptiveObject):
    """Configuration for the CL service."""

    type: Literal["docker-compose", "docker"] = Field(description="Service type")


class DockerComposeServiceConfig(ServiceConfig):
    """Configuration for the Docker Compose service."""

    type: Literal["docker-compose"] = Field(description="Service type")
    file: str = Field(default="docker-compose.yml", description="Entrypoint file path")
    required_healthy_containers: List[str] = Field(
        default=["*"],
        description="List of services to wait for (use ['*'] for all services)",
    )
    healthy_wait_timeout: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="Timeout in seconds to wait for services to become healthy",
    )
    volumes: Optional[List[str]] = Field(default=None, description="Volumes to mount")


class ListenerConfig(AdaptiveObject):
    """Configuration for the listener."""

    type: Literal["db", "proxy", "file"] = Field(description="Listener type")


class DatabaseMutationListenerConfig(ListenerConfig):
    """Mutation listener configuration for database monitoring."""

    type: Literal["db"] = Field(description="Listener type")
    db_type: Literal["postgresql", "mysql", "sqlite"] = Field(
        description="Database type"
    )
    db_host: str = Field(description="Database host")
    db_port: int = Field(ge=1, le=65535, description="Database port")
    db_user: str = Field(description="Database user")
    db_password: str = Field(description="Database password")
    db_database: str = Field(description="Database name")
    schema: Optional[str] = Field(
        default="public", description="Database schema (for PostgreSQL)"
    )
    seed_data_paths: Optional[List[str]] = Field(
        default=None, description="Seed data paths"
    )
    truncate_tables: Optional[bool] = Field(
        default=None, description="Truncate tables before seed restore"
    )
    audit_ignore_tables: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=None, description="Tables or patterns the auditor should ignore"
    )


class ProxyMutationListenerConfig(ListenerConfig):
    """Mutation listener configuration for proxy monitoring."""

    type: Literal["proxy"] = Field(description="Listener type")
    sim_name: Optional[str] = Field(default=None, description="Name of the simulation")
    dataset: Optional[str] = Field(default=None, description="Dataset to use")
    proxy_host: str = Field(default="localhost", description="Proxy server host")
    proxy_port: int = Field(
        default=8888, ge=1024, le=65535, description="Proxy server port"
    )
    passthrough_all_ood_requests: bool = Field(
        default=True, description="Whether to pass through out-of-domain requests"
    )
    replay_sessions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Replay sessions configuration"
    )


class FileMutationListenerConfig(ListenerConfig):
    """Mutation listener configuration for file monitoring."""

    type: Literal["file"] = Field(description="Listener type")
    seed_data_path: Optional[str] = Field(default=None, description="Seed data path")
    target_dir: str = Field(description="Main directory for file monitoring")
    watch_enabled: bool = Field(default=True, description="Enable mutation tracking")
    watch_patterns: Optional[List[str]] = Field(
        default_factory=lambda: ["*"], description="Glob patterns to watch"
    )
    ignore_patterns: Optional[List[str]] = Field(
        default_factory=list, description="Glob patterns to ignore"
    )
    scan_frequency: int = Field(
        default=5, description="State rescan frequency in seconds"
    )


class DatasetConfig(BaseModel):
    """Dataset configuration with services and listeners."""

    services: List[ServiceConfig] = Field(
        default_factory=list, description="Services to run"
    )
    listeners: List[ListenerConfig] = Field(
        default_factory=list, description="Listeners to use"
    )


class PlatoConfig(BaseModel):
    """Main Plato configuration structure."""

    compute: ComputeConfig = Field(default_factory=ComputeConfig)
    datasets: Dict[str, DatasetConfig] = Field(description="Available datasets")


# Load environment variables from multiple possible locations
load_dotenv()  # Load from current directory
load_dotenv(
    dotenv_path=os.path.join(os.path.expanduser("~"), ".env")
)  # Load from home directory
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), ".env")
)  # Load from script directory


def handle_async(coro):
    """Helper function to run async functions in CLI commands."""
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        console.print("[red]Operation cancelled by user.[/red]", style="bold")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", style="bold")
        # Check if it's an auth issue and provide helpful hint
        if "401" in str(e) or "Unauthorized" in str(e):
            console.print(
                "💡 [yellow]Hint: Make sure PLATO_API_KEY is set in your environment or .env file[/yellow]"
            )
        raise typer.Exit(1)


# Main CLI app is already defined above


@app.command()
def make(
    env_name: str = typer.Argument(
        ..., help="The name of the environment to create (e.g., 'espocrm', 'doordash')"
    ),
    interface_type: str = typer.Option(
        "browser", help="Interface type for the environment"
    ),
    width: int = typer.Option(1920, help="Viewport width"),
    height: int = typer.Option(1080, help="Viewport height"),
    keepalive: bool = typer.Option(
        False, "--keepalive", help="Keep environment alive (disable heartbeat timeout)"
    ),
    alias: Optional[str] = typer.Option(None, help="Alias for the job group"),
    open_page: bool = typer.Option(False, "--open-page", help="Open page on start"),
):
    """
    [bold green]Create a new Plato environment.[/bold green]

    Creates and initializes a new Plato environment with the specified configuration.
    """

    async def _make():
        client = Plato()
        try:
            with console.status(
                f"[bold green]Creating environment '{env_name}'...", spinner="dots"
            ):
                env = await client.make_environment(
                    env_id=env_name,
                    interface_type=interface_type,
                    viewport_width=width,
                    viewport_height=height,
                    keepalive=keepalive,
                    alias=alias,
                    open_page_on_start=open_page,
                )

            # Success panel
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

            # Wait for environment to be ready with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Waiting for environment to be ready...", total=None
                )
                await env.wait_for_ready(timeout=300.0)
                progress.update(task, description="[green]Environment is ready!")

            # Get public URL
            try:
                public_url = await env.get_public_url()
                url_panel = Panel.fit(
                    f"[blue]{public_url}[/blue]",
                    title="[bold blue]🌐 Public URL[/bold blue]",
                    border_style="blue",
                )
                console.print(url_panel)
            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Warning: Could not get public URL: {e}[/yellow]"
                )

            return env

        finally:
            await client.close()

    handle_async(_make())


@app.command()
def reset(
    env_id: str = typer.Argument(..., help="The ID of the environment to reset"),
    task_id: Optional[str] = typer.Option(
        None, "--task-id", help="Optional task ID to reset with"
    ),
    agent_version: Optional[str] = typer.Option(
        None, "--agent-version", help="Optional agent version"
    ),
):
    """
    [bold yellow]Reset an existing Plato environment.[/bold yellow]

    Resets the specified environment to a clean state.
    """

    async def _reset():
        client = Plato()
        try:
            # For reset, we need to create a temporary environment object
            # Since we only have the ID, we'll create it with minimal info
            from plato.models.env import PlatoEnvironment

            env = PlatoEnvironment(client=client, id=env_id)

            with console.status(
                f"[bold yellow]Resetting environment '{env_id}'...", spinner="dots"
            ):
                # Load task if task_id is provided
                task = None
                if task_id:
                    console.print(
                        f"[cyan]Note: Task ID '{task_id}' will be used for reset[/cyan]"
                    )

                session_id = await env.reset(task=task, agent_version=agent_version)

            # Success panel
            reset_panel = Panel.fit(
                f"[green]Environment reset successfully![/green]\n"
                f"[cyan]Session ID:[/cyan] [bold]{session_id}[/bold]",
                title="[bold green]🔄 Reset Complete[/bold green]",
                border_style="green",
            )
            console.print(reset_panel)

        finally:
            await client.close()

    handle_async(_reset())


@app.command()
def state(
    env_id: str = typer.Argument(..., help="The ID of the environment to check"),
    pretty: bool = typer.Option(
        True, "--pretty/--no-pretty", help="Pretty print JSON output"
    ),
    mutations: bool = typer.Option(
        False, "--mutations", help="Show only state mutations"
    ),
):
    """
    [bold blue]Get the current state of a Plato environment.[/bold blue]

    Displays the current state or state mutations of the specified environment.
    """

    async def _state():
        client = Plato()
        try:
            # Create a temporary environment object to get state
            from plato.models.env import PlatoEnvironment

            env = PlatoEnvironment(client=client, id=env_id)

            with console.status(
                f"[bold blue]Getting state for environment '{env_id}'...",
                spinner="dots",
            ):
                if mutations:
                    state_data = await env.get_state_mutations()
                    title = f"State Mutations ({len(state_data)} mutations)"
                else:
                    state_data = await env.get_state()
                    title = "Environment State"

            # Display in a nice panel
            if pretty:
                formatted_json = json.dumps(state_data, indent=2)
            else:
                formatted_json = json.dumps(state_data)

            state_panel = Panel(
                formatted_json,
                title=f"[bold blue]📊 {title}[/bold blue]",
                border_style="blue",
                expand=False,
            )
            console.print(state_panel)

        except PlatoClientError as e:
            if "No active run session" in str(e):
                console.print(
                    f"[red]Error: Environment '{env_id}' has no active run session.[/red]\n"
                    f"[yellow]💡 Try resetting it first.[/yellow]"
                )
                raise typer.Exit(1)
            else:
                raise
        finally:
            await client.close()

    handle_async(_state())


@app.command()
def status(
    env_id: str = typer.Argument(..., help="The ID of the environment to check"),
):
    """
    [bold cyan]Get the status of a Plato environment.[/bold cyan]

    Displays detailed status information for the specified environment.
    """

    async def _status():
        client = Plato()
        try:
            with console.status(
                f"[bold cyan]Getting status for environment '{env_id}'...",
                spinner="dots",
            ):
                status_data = await client.get_job_status(env_id)

            # Create a nice status table
            table = Table(
                title=f"[bold cyan]📊 Environment Status: {env_id}[/bold cyan]"
            )
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="green")

            # Add key status information
            status_value = status_data.get("status", "unknown")
            status_color = {
                "running": "green",
                "completed": "blue",
                "failed": "red",
                "pending": "yellow",
            }.get(status_value.lower(), "white")

            table.add_row("Status", f"[{status_color}]{status_value}[/{status_color}]")

            if "message" in status_data:
                table.add_row("Message", status_data["message"])

            # Add other relevant fields
            for key, value in status_data.items():
                if key not in ["status", "message"]:
                    table.add_row(key.replace("_", " ").title(), str(value))

            console.print(table)

            # Show full JSON in a collapsible panel
            if len(status_data) > 3:  # Only show if there's more detailed data
                json_panel = Panel(
                    json.dumps(status_data, indent=2),
                    title="[bold white]📄 Full Status JSON[/bold white]",
                    border_style="white",
                    expand=False,
                )
                console.print("\n")
                console.print(json_panel)

        finally:
            await client.close()

    handle_async(_status())


@app.command()
def close(env_id: str = typer.Argument(..., help="The ID of the environment to close")):
    """
    [bold red]Close a Plato environment and clean up resources.[/bold red]

    Safely shuts down and cleans up the specified environment.
    """

    async def _close():
        client = Plato()
        try:
            with console.status(
                f"[bold red]Closing environment '{env_id}'...", spinner="dots"
            ):
                response = await client.close_environment(env_id)

            # Success panel
            close_panel = Panel.fit(
                f"[green]Environment closed successfully![/green]\n"
                f"[dim]{json.dumps(response, indent=2)}[/dim]",
                title="[bold green]🚪 Environment Closed[/bold green]",
                border_style="green",
            )
            console.print(close_panel)

        finally:
            await client.close()

    handle_async(_close())


@app.command()
def url(env_id: str = typer.Argument(..., help="The ID of the environment")):
    """
    [bold blue]Get the public URL for a Plato environment.[/bold blue]

    Retrieves and displays the public URL for accessing the environment.
    """

    async def _url():
        client = Plato()
        try:
            # Create a temporary environment object to get public URL
            from plato.models.env import PlatoEnvironment

            env = PlatoEnvironment(client=client, id=env_id)

            with console.status(
                f"[bold blue]Getting public URL for '{env_id}'...", spinner="dots"
            ):
                public_url = await env.get_public_url()

            # Display URL in a nice panel
            url_panel = Panel.fit(
                f"[blue]{public_url}[/blue]",
                title=f"[bold blue]🌍 Public URL for '{env_id}'[/bold blue]",
                border_style="blue",
            )
            console.print(url_panel)

        finally:
            await client.close()

    handle_async(_url())


@app.command()
def list_simulators():
    """
    [bold magenta]List all available simulators/environments.[/bold magenta]

    Displays a table of all available simulators with their status and descriptions.
    """

    async def _list():
        client = Plato()
        try:
            with console.status(
                "[bold magenta]Fetching available simulators...", spinner="dots"
            ):
                simulators = await client.list_simulators()

            if not simulators:
                console.print("[yellow]No simulators found.[/yellow]")
                return

            # Create a nice table
            table = Table(title="[bold magenta]🎮 Available Simulators[/bold magenta]")
            table.add_column("Status", justify="center", style="green", no_wrap=True)
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")

            for sim in simulators:
                status_icon = "✅" if sim.get("enabled", False) else "❌"
                status_text = "Enabled" if sim.get("enabled", False) else "Disabled"
                description = sim.get("description", "No description")

                table.add_row(f"{status_icon} {status_text}", sim["name"], description)

            console.print(table)
            console.print(f"\n[dim]Found {len(simulators)} simulators total[/dim]")

        finally:
            await client.close()

    handle_async(_list())


# Helper functions for hub git operations
def _hub_push(hub_config: dict, extra_args: list):
    """Push current directory contents to simulator repository"""
    import tempfile
    import shutil
    import subprocess

    try:
        clone_url = _get_authenticated_url(hub_config)
        if not clone_url:
            console.print(
                "[red]❌ Authentication failed. Run 'uv run plato hub login' first.[/red]"
            )
            return

        sim_name = hub_config["simulator_name"]

        console.print(f"📤 Pushing to simulator '{sim_name}'...")

        # Create temporary directory for isolated git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, "temp_repo")

            # Clone the simulator repository
            result = subprocess.run(
                ["git", "clone", clone_url, temp_repo], capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print(
                    f"❌ Failed to clone simulator repo: {result.stderr.strip()}",
                )
                return

            # Copy current directory contents to temp repo (excluding git and config files)
            current_dir = os.getcwd()
            for item in os.listdir(current_dir):
                if item.startswith("."):
                    continue  # Skip hidden files

                src = os.path.join(current_dir, item)
                dst = os.path.join(temp_repo, item)

                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)

            # Commit and push changes
            os.chdir(temp_repo)
            subprocess.run(["git", "add", "."], check=True)

            # Check if there are changes to commit
            status_result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            )
            if not status_result.stdout.strip():
                console.print("[yellow]📝 No changes to push[/yellow]")
                return

            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"Sync from {hub_config['sync_directory']} directory",
                ],
                check=True,
            )

            # Push to main branch (or specified branch)
            push_args = ["git", "push", "origin", "main"] + extra_args
            result = subprocess.run(push_args, capture_output=True, text=True)

            if result.returncode == 0:
                console.print(
                    f"[green]✅ Successfully pushed to simulator '{sim_name}'"
                )
            else:
                console.print(f"[red]❌ Push failed: {result.stderr.strip()}")

    except Exception as e:
        console.print(f"[red]❌ Error during push: {e}")


def _hub_pull(hub_config: dict, extra_args: list):
    """Pull changes from simulator repository to current directory"""
    import tempfile
    import subprocess
    import shutil

    try:
        clone_url = _get_authenticated_url(hub_config)
        if not clone_url:
            console.print(
                "[red]❌ Authentication failed. Run 'uv run plato hub login' first.[/red]"
            )
            return

        sim_name = hub_config["simulator_name"]

        console.print(f"📥 Pulling from simulator '{sim_name}'...")

        # Create temporary directory for isolated git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, "temp_repo")

            # Clone the simulator repository
            result = subprocess.run(
                ["git", "clone", clone_url, temp_repo], capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print(
                    f"❌ Failed to clone simulator repo: {result.stderr.strip()}",
                )
                return

            # Copy contents from temp repo to current directory (excluding git files)
            current_dir = os.getcwd()
            for item in os.listdir(temp_repo):
                if item.startswith(".git"):
                    continue  # Skip git directory

                src = os.path.join(temp_repo, item)
                dst = os.path.join(current_dir, item)

                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                        shutil.copytree(src, dst)

            console.print(f"[green]✅ Successfully pulled from simulator '{sim_name}'")
            console.print(
                "💡 Files updated in current directory. Review and commit to your monorepo as needed."
            )

    except Exception as e:
        console.print(f"[red]❌ Error during pull: {e}")


async def _wait_for_vm_ready(client: "Plato", correlation_id: str, timeout: int = 300):
    """Wait for VM to be ready by monitoring SSE stream"""
    import aiohttp
    import json
    import base64
    import time

    start_time = time.time()

    try:
        async with client.http_session.get(
            f"{client.base_url}/public-build/events/{correlation_id}",
            headers={"X-API-Key": client.api_key},
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to connect to event stream: {response.status}")

            async for line in response.content:
                if time.time() - start_time > timeout:
                    raise Exception(f"VM startup timed out after {timeout} seconds")

                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    try:
                        # Decode base64 data
                        encoded_data = line_str[6:]  # Remove 'data: ' prefix
                        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
                        event_data = json.loads(decoded_data)

                        if event_data.get("event_type") == "completed":
                            # Show success panel
                            vm_panel = Panel.fit(
                                "[green]Virtual machine is now running and ready![/green]\n"
                                "[dim]VM resources allocated and services initialized[/dim]",
                                title="[bold green]🟢 VM Startup Complete[/bold green]",
                                border_style="green",
                            )
                            console.print(vm_panel)
                            return True
                        elif event_data.get("event_type") == "failed":
                            error = event_data.get("error", "Unknown error")
                            raise Exception(f"VM startup failed: {error}")
                        else:
                            # Show progress with status
                            message = event_data.get("message", "Starting...")
                            with console.status(
                                f"[cyan]🚀 {message}...", spinner="dots"
                            ):
                                pass

                    except (json.JSONDecodeError, base64.binascii.Error):
                        continue  # Skip malformed lines

    except Exception as e:
        console.print(f"[red]❌ Error waiting for VM: {e}")
        return False


async def _monitor_ssh_execution(
    client: "Plato", correlation_id: str, operation_name: str, timeout: int = 600
) -> bool:
    """Monitor SSH command execution via SSE and show output."""
    result = await _monitor_ssh_execution_with_data(
        client, correlation_id, operation_name, timeout
    )
    return result is not None and result.get("success", False)


async def _monitor_ssh_execution_with_data(
    client: "Plato", correlation_id: str, operation_name: str, timeout: int = 600
) -> dict:
    """Monitor SSH command execution via SSE and return event data."""
    import aiohttp
    import json
    import base64
    import time

    start_time = time.time()

    try:
        async with client.http_session.get(
            f"{client.base_url}/public-build/events/{correlation_id}",
            headers={"X-API-Key": client.api_key},
        ) as response:
            if response.status != 200:
                console.print(
                    f"❌ Failed to connect to event stream: {response.status}"
                )
                return None

            async for line in response.content:
                if time.time() - start_time > timeout:
                    console.print(f"⏰ Operation timed out after {timeout} seconds")
                    return None

                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    try:
                        # Decode base64 data
                        encoded_data = line_str[6:]  # Remove 'data: ' prefix
                        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
                        event_data = json.loads(decoded_data)

                        event_type = event_data.get("event_type", "unknown")

                        if event_type == "completed":
                            # Show command output
                            stdout = event_data.get("stdout", "")
                            stderr = event_data.get("stderr", "")

                            if stdout and stdout.strip():
                                console.print("📤 [green]Command Output:[/green]")
                                for line in stdout.strip().split("\n"):
                                    console.print(f"   {line}")

                            if stderr and stderr.strip():
                                # Filter SSH warnings
                                filtered_stderr = _filter_ssh_warnings(stderr)
                                if filtered_stderr and filtered_stderr.strip():
                                    console.print("📤 [red]Error Output:[/red]")
                                    for line in filtered_stderr.strip().split("\n"):
                                        console.print(f"   {line}")

                            return {
                                "success": True,
                                "stdout": stdout,
                                "stderr": stderr,
                                "event_data": event_data,
                            }

                        elif event_type == "failed":
                            error = event_data.get("error", "Unknown error")
                            stdout = event_data.get("stdout", "")
                            stderr = event_data.get("stderr", "")

                            console.print(
                                f"❌ [red]{operation_name} failed: {error}[/red]"
                            )

                            if stdout and stdout.strip():
                                console.print("📤 [yellow]Command Output:[/yellow]")
                                for line in stdout.strip().split("\n"):
                                    console.print(f"   {line}")

                            if stderr and stderr.strip():
                                # Filter SSH warnings
                                filtered_stderr = _filter_ssh_warnings(stderr)
                                if filtered_stderr and filtered_stderr.strip():
                                    console.print("📤 [red]Error Output:[/red]")
                                    for line in filtered_stderr.strip().split("\n"):
                                        console.print(f"   {line}")

                            return {
                                "success": False,
                                "stdout": stdout,
                                "stderr": stderr,
                                "event_data": event_data,
                                "error": error,
                            }

                    except (json.JSONDecodeError, base64.binascii.Error):
                        continue  # Skip malformed lines

    except Exception as e:
        console.print(f"❌ Error monitoring {operation_name}: {e}")
        return None

    console.print(f"❌ {operation_name} stream ended without completion")
    return None


async def _wait_for_setup_ready(
    client: "Plato", correlation_id: str, timeout: int = 600
):
    """Wait for sandbox setup to complete by monitoring SSE stream and capture SSH key"""
    import aiohttp
    import json
    import base64
    import time
    import re
    import os

    start_time = time.time()

    try:
        async with client.http_session.get(
            f"{client.base_url}/public-build/events/{correlation_id}",
            headers={"X-API-Key": client.api_key},
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to connect to setup stream: {response.status}")

            async for line in response.content:
                if time.time() - start_time > timeout:
                    console.print(
                        f"⏰ Timeout reached after {timeout} seconds ({timeout // 60} minutes)"
                    )
                    console.print(
                        f"[red]Setup is taking longer than expected - this may indicate a problem[/red]"
                    )
                    raise Exception(f"Sandbox setup timed out after {timeout} seconds")

                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    try:
                        # Decode base64 data
                        encoded_data = line_str[6:]  # Remove 'data: ' prefix
                        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
                        event_data = json.loads(decoded_data)

                        # Debug: Show all event types for troubleshooting
                        event_type = event_data.get("event_type", "unknown")
                        console.print(
                            f"[dim]🔍 Event: '{event_type}' | Complete: {event_data.get('is_workflow_complete', False)} | Message: {event_data.get('message', 'none')}[/dim]"
                        )

                        if event_data.get("event_type") == "completed":
                            console.print(f"[green]✅ SANDBOX SETUP COMPLETED")
                            success_panel = Panel.fit(
                                "[green]Sandbox setup completed successfully![/green]\n"
                                "[dim]All setup steps completed - environment is ready[/dim]",
                                title="[bold green]🎉 Setup Complete[/bold green]",
                                border_style="green",
                            )
                            console.print(success_panel)
                            return True

                        elif event_data.get("event_type") == "failed":
                            error = event_data.get("error", "Unknown error")
                            stdout = event_data.get("stdout", "")
                            stderr = event_data.get("stderr", "")
                            message = event_data.get("message", "")

                            console.print(f"[red]❌ SANDBOX SETUP FAILED")
                            console.print(f"[red]Failed Step: {message}")
                            console.print(f"[red]Error: {error}")

                            if stdout and stdout.strip():
                                console.print(f"[yellow]📤 Command Output:")
                                for line in stdout.strip().split("\n"):
                                    console.print(f"   {line}")

                            if stderr and stderr.strip():
                                # Filter SSH warnings here too
                                stderr_lines = stderr.strip().split("\n")
                                real_errors = []
                                for line in stderr_lines:
                                    if not any(
                                        warning in line
                                        for warning in [
                                            "Warning: Permanently added",
                                            "Warning: Known hosts file",
                                            "debconf: unable to initialize frontend",
                                            "debconf: falling back to frontend",
                                            "WARNING! Your credentials are stored unencrypted",
                                            "Configure a credential helper to remove this warning",
                                        ]
                                    ):
                                        real_errors.append(line)

                                if real_errors:
                                    console.print(f"[red]📤 Error Details:")
                                    for line in real_errors:
                                        console.print(f"   {line}")

                            raise Exception(f"Sandbox setup failed at step: {message}")

                        # Handle workflow-level completion - this is the proper success indicator
                        elif event_data.get("event_type") == "workflow_completed" or (
                            event_data.get("event_type") == "completed"
                            and event_data.get("is_workflow_complete")
                        ):
                            console.print(f"[green]✅ SANDBOX WORKFLOW COMPLETED")
                            success_panel = Panel.fit(
                                "[green]Sandbox setup completed successfully![/green]\n"
                                "[dim]All workflow steps completed - environment is ready[/dim]",
                                title="[bold green]🎉 Setup Complete[/bold green]",
                                border_style="green",
                            )
                            console.print(success_panel)
                            return True

                    except (json.JSONDecodeError, base64.binascii.Error):
                        continue  # Skip malformed lines

    except Exception as e:
        console.print(f"[red]❌ Error waiting for sandbox setup: {e}")
        return False

    # If we exit the loop without seeing "Chisel server started successfully", that's a failure
    console.print(f"[red]❌ Setup stream ended without success confirmation")
    console.print(
        f"[red]Expected to see 'Chisel server started successfully' but didn't"
    )
    return False


def _setup_local_ssh_key():
    """Generate local SSH key pair for sandbox access"""
    import os
    import subprocess

    try:
        # Create SSH directory if it doesn't exist
        ssh_dir = os.path.expanduser("~/.ssh")
        os.makedirs(ssh_dir, exist_ok=True)

        # Generate local SSH key pair if it doesn't exist
        local_key_path = os.path.join(ssh_dir, "plato_sandbox_key")
        if not os.path.exists(local_key_path):
            subprocess.run(
                [
                    "ssh-keygen",
                    "-t",
                    "rsa",
                    "-b",
                    "2048",
                    "-f",
                    local_key_path,
                    "-N",
                    "",
                    "-C",
                    "plato-sandbox-client",
                ],
                check=True,
                capture_output=True,
            )

            # Set proper permissions
            os.chmod(local_key_path, 0o600)
            os.chmod(f"{local_key_path}.pub", 0o644)

            console.print(f"🔑 [green]Generated SSH key pair: {local_key_path}[/green]")

        # Read our public key to send to the VM
        with open(f"{local_key_path}.pub", "r") as f:
            local_public_key = f.read().strip()

        console.print(f"🔑 [green]SSH key ready for passwordless access[/green]")
        return local_key_path, local_public_key

    except Exception as e:
        console.print(
            f"[yellow]⚠️  [yellow]Warning: Failed to setup SSH key: {e}[/yellow]"
        )
        return None, None


async def _create_default_config(config_path: str):
    """Create a default plato-config.yml file with standard VM specifications."""
    import yaml

    # Create default config with base dataset
    default_config = PlatoConfig(
        compute=ComputeConfig(),
        datasets={
            "base": DatasetConfig(
                services=[
                    DockerComposeServiceConfig(
                        type="docker-compose",
                        file="datasets/base/docker-compose.yml",
                        required_healthy_containers=["*"],
                        healthy_wait_timeout=300,
                    )
                ],
                listeners=[
                    DatabaseMutationListenerConfig(
                        type="db",
                        db_type="postgresql",
                        db_host="base-db.internal",
                        db_port=5432,
                        db_user="base_user",
                        db_password="${BASE_DB_PASSWORD}",
                        db_database="base_db",
                    )
                ],
            )
        },
    )

    try:
        with open(config_path, "w") as f:
            # Convert Pydantic model to dict and write as YAML
            yaml.dump(
                default_config.model_dump(),
                f,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
            )
    except Exception as e:
        console.print(f"[red]❌ Failed to create default config: {e}")
        raise


def _filter_ssh_warnings(stderr: str) -> str:
    """Filter out common SSH warnings that clutter output."""
    if not stderr:
        return ""

    lines = stderr.strip().split("\n")
    filtered_lines = []

    for line in lines:
        # Skip common SSH warnings
        if any(
            warning in line
            for warning in [
                "Warning: Permanently added",
                "Warning: Known hosts file",
                "debconf: unable to initialize frontend",
                "debconf: falling back to frontend",
                "WARNING! Your credentials are stored unencrypted",
                "Configure a credential helper to remove this warning",
            ]
        ):
            continue
        filtered_lines.append(line)

    return "\n".join(filtered_lines)


async def _wait_for_sim_ready(
    client: "Plato", vm_job_uuid: str, timeout: int = 600
) -> bool:
    """Wait for simulator to be fully initialized by checking status file."""
    import time
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    start_time = time.time()
    last_status = "unknown"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "⏳ Waiting for simulator initialization...", total=None
        )

        while time.time() - start_time < timeout:
            try:
                # Use the proper sim-status endpoint
                status_response = await client.http_session.get(
                    f"{client.base_url}/public-build/vm/{vm_job_uuid}/sim-status",
                    headers={"X-API-Key": client.api_key},
                )

                if status_response.status == 200:
                    response_data = await status_response.json()
                    sse_stream_url = response_data.get("sse_stream_url")
                    correlation_id = response_data.get("correlation_id")

                    if sse_stream_url and correlation_id:
                        console.print(f"🔗 Monitoring via SSE: {sse_stream_url}")

                        status_result = await _monitor_ssh_execution_with_data(
                            client, correlation_id, "Status check", timeout=30
                        )

                        if status_result and status_result.get("success"):
                            # Parse the status from the command output
                            stdout = status_result.get("stdout", "")
                            if stdout and stdout.strip():
                                try:
                                    # Clean up the JSON string by removing invalid control characters
                                    cleaned_stdout = stdout.strip()
                                    # Replace problematic control characters that break JSON parsing
                                    import re

                                    # Remove or replace control characters except for \n, \r, \t
                                    cleaned_stdout = re.sub(
                                        r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]",
                                        "",
                                        cleaned_stdout,
                                    )

                                    status_data = json.loads(cleaned_stdout)
                                    sim_status = status_data.get("status", "unknown")
                                    message = status_data.get("message", "")
                                    timestamp = status_data.get("timestamp", "")

                                    # Only show if status changed
                                    if sim_status != last_status:
                                        # Format status nicely - truncate long messages for display
                                        display_message = message
                                        if len(message) > 200:
                                            display_message = message[:200] + "..."

                                        status_panel = Panel.fit(
                                            f"[bold]Status:[/bold] {sim_status}\n"
                                            f"[bold]Message:[/bold] {display_message}\n"
                                            f"[bold]Time:[/bold] {timestamp}",
                                            title=f"[bold cyan]📊 Simulator Status[/bold cyan]",
                                            border_style="cyan",
                                        )
                                        console.print(status_panel)
                                        last_status = sim_status

                                    if sim_status == "ready":
                                        progress.update(
                                            task, description="✅ Simulator ready!"
                                        )
                                        console.print(
                                            f"[green]🎉 Simulator initialization completed![/green]"
                                        )
                                        return True
                                    elif sim_status == "failed":
                                        progress.update(
                                            task, description="❌ Initialization failed"
                                        )
                                        # Show full error message for failed status
                                        console.print(
                                            f"[red]❌ Simulator initialization failed![/red]"
                                        )
                                        console.print(
                                            f"[yellow]Error details:[/yellow] {message}"
                                        )
                                        return False
                                    elif sim_status in ["pending", "initializing"]:
                                        elapsed = int(time.time() - start_time)
                                        if elapsed > 300:
                                            console.print(
                                                "[red]❌ Taking too long - likely database issue[/red]"
                                            )
                                            return False
                                        else:
                                            progress.update(
                                                task,
                                                description=f"⏳ {sim_status.title()}... ({elapsed}s)",
                                            )
                                    elif sim_status == "unknown":
                                        # Handle unknown status (like "Status file not found")
                                        elapsed = int(time.time() - start_time)
                                        if (
                                            elapsed > 60
                                        ):  # Give more time for initial startup
                                            progress.update(
                                                task,
                                                description=f"⏳ Starting up... ({elapsed}s)",
                                            )

                                except json.JSONDecodeError as e:
                                    console.print(
                                        f"⚠️ Could not parse status JSON: {e} - retrying..."
                                    )
                                    console.print(
                                        f"Raw output: {stdout.strip()[:100]}..."
                                    )
                        else:
                            console.print("⚠️ Status check failed - retrying...")

                    await asyncio.sleep(5)
                else:
                    console.print(f"❌ Status check failed: {status_response.status}")
                    await asyncio.sleep(5)

            except Exception as e:
                console.print(f"[yellow]⚠️  Error checking status: {e}[/yellow]")
                await asyncio.sleep(5)

    console.print(
        f"[red]❌ Simulator initialization timed out after {timeout} seconds[/red]"
    )
    console.print(
        "💡 [yellow]Check the simulator service logs: journalctl -u <service>-simulator -f[/yellow]"
    )
    return False


async def _setup_sandbox(
    client: "Plato",
    vm_job_uuid: str,
    dev_branch: str,
    clone_url: str,
    chisel_port: int = 6000,
):
    """Setup the sandbox environment with code and chisel SSH"""
    import json
    import uuid

    try:
        # Generate local SSH key for passwordless access
        # Show SSH setup panel
        ssh_panel = Panel.fit(
            "[cyan]Generating secure SSH key pair for passwordless access[/cyan]",
            title="[bold cyan]🔑 SSH Authentication Setup[/bold cyan]",
            border_style="cyan",
        )
        console.print(ssh_panel)
        local_key_path, local_public_key = _setup_local_ssh_key()

        # Setup sandbox environment via new endpoint
        setup_data = {
            "branch": dev_branch,
            "clone_url": clone_url,
            "chisel_port": chisel_port,
            "timeout": 300,
        }

        # Add client SSH public key if available
        if local_public_key:
            setup_data["client_ssh_public_key"] = local_public_key
            console.print(
                "🔑 [green]Sending SSH public key for passwordless access[/green]"
            )

        setup_response = await client.http_session.post(
            f"{client.base_url}/public-build/vm/{vm_job_uuid}/setup-sandbox",
            json=setup_data,
            headers={"X-API-Key": client.api_key},
        )

        if setup_response.status != 200:
            error = await setup_response.text()
            console.print(f"[red]❌ [red]Failed to setup sandbox: {error}[/red]")
            return None

        return await setup_response.json()

    except Exception as e:
        console.print(f"[red]❌ [red]Error setting up sandbox: {e}[/red]")
        return None


async def _run_interactive_sandbox(sandbox_info: dict, client: "Plato", keep_vm: bool):
    """Run interactive sandbox mode with editor integration"""
    import subprocess
    import os

    vm_job_uuid = sandbox_info["vm_job_uuid"]
    ssh_url = sandbox_info["ssh_url"]

    # Setup local chisel client for SSH tunneling
    local_port = await _setup_chisel_client(ssh_url)
    if not local_port:
        console.print("❌ Failed to setup local chisel client")
        return

    # Ask permission and set up SSH config with unique host name
    ssh_host = None
    if Confirm.ask("💡 Set up SSH config for easy connection?", default=True):
        ssh_host = _setup_ssh_config_with_password(local_port, vm_job_uuid)

    # Store ssh_host for use in commands
    sandbox_info["ssh_host"] = ssh_host or f"plato-sandbox-{vm_job_uuid[:8]}"

    console.print(
        Panel.fit(
            "[bold green]Sandbox is ready![/bold green] Choose an action:",
            title="[bold blue]🚀 Interactive Sandbox[/bold blue]",
            border_style="blue",
        )
    )

    while True:
        # Create a menu table
        menu_table = Table(title="[bold cyan]📋 Sandbox Menu[/bold cyan]")
        menu_table.add_column("Option", style="cyan", no_wrap=True)
        menu_table.add_column("Action", style="white")

        menu_table.add_row("1", "Start Listeners")
        menu_table.add_row("2", "Stop Listeners")
        menu_table.add_row("3", "Start Services")
        menu_table.add_row("4", "Stop Services")
        menu_table.add_row("5", "Listeners - Reset")
        menu_table.add_row("6", "Listeners - Backup")
        menu_table.add_row("7", "Open VS Code connected to sandbox")
        menu_table.add_row("8", "Open Cursor connected to sandbox")
        menu_table.add_row("9", "Create VM snapshot")
        menu_table.add_row("10", "Show VM info")
        menu_table.add_row("11", "Stop sandbox and cleanup")
        menu_table.add_row("12", "Start All")

        console.print("\n")
        console.print(menu_table)

        try:
            choice = typer.prompt("Choose an action (1-12)", type=int)
        except (KeyboardInterrupt, EOFError):
            break

        if choice == 1:
            # Start Listeners
            console.print(f"🚀 [cyan]Starting listeners...[/cyan]")
            try:
                with console.status("[cyan]🚀 Starting listeners...", spinner="dots"):
                    resp = await client.http_session.post(
                        f"{client.base_url}/public-build/vm/{sandbox_info['vm_job_uuid']}/start-listeners",
                        json={
                            "dataset": sandbox_info.get("dataset", "base"),
                            "plato_config": sandbox_info.get("plato_config", {}),
                            "plato_worker_version": None,
                            "timeout": 600,
                        },
                        headers={"X-API-Key": client.api_key},
                    )
                if resp.status == 200:
                    data = await resp.json()
                    correlation_id = data.get("correlation_id")
                    if correlation_id:
                        console.print("⏳ [cyan]Monitoring listener startup...[/cyan]")
                        await _monitor_ssh_execution(
                            client, correlation_id, "Start listeners", timeout=180
                        )
                else:
                    err = await resp.text()
                    console.print(f"❌ [red]Failed to start listeners: {err}")
            except Exception as e:
                console.print(f"❌ [red]Error starting listeners: {e}[/red]")

        elif choice == 2:
            # Stop Listeners
            console.print(f"🛑 [cyan]Stopping listeners...[/cyan]")
            try:
                resp = await client.http_session.post(
                    f"{client.base_url}/public-build/vm/{sandbox_info['vm_job_uuid']}/stop-listeners",
                    json={
                        "dataset": sandbox_info.get("dataset", "base"),
                        "timeout": 300,
                    },
                    headers={"X-API-Key": client.api_key},
                )
                if resp.status == 200:
                    data = await resp.json()
                    correlation_id = data.get("correlation_id")
                    if correlation_id:
                        await _monitor_ssh_execution(
                            client, correlation_id, "Stop listeners", timeout=120
                        )
                else:
                    err = await resp.text()
                    console.print(f"❌ [red]Failed to stop listeners: {err}")
            except Exception as e:
                console.print(f"❌ [red]Error stopping listeners: {e}[/red]")

        elif choice == 3:
            # Start Services
            console.print(f"🚀 [cyan]Starting services...[/cyan]")
            try:
                with console.status("[cyan]🚀 Starting services...", spinner="dots"):
                    resp = await client.http_session.post(
                        f"{client.base_url}/public-build/vm/{sandbox_info['vm_job_uuid']}/start-services",
                        json={
                            "dataset": sandbox_info.get("dataset", "base"),
                            "plato_config": sandbox_info.get("plato_config", {}),
                            "timeout": 600,
                        },
                        headers={"X-API-Key": client.api_key},
                    )
                if resp.status == 200:
                    data = await resp.json()
                    correlation_id = data.get("correlation_id")
                    if correlation_id:
                        await _monitor_ssh_execution(
                            client, correlation_id, "Start services", timeout=300
                        )
                else:
                    err = await resp.text()
                    console.print(f"❌ [red]Failed to start services: {err}")
            except Exception as e:
                console.print(f"❌ [red]Error starting services: {e}[/red]")

        elif choice == 4:
            # Stop Services
            console.print(f"🛑 [cyan]Stopping services...[/cyan]")
            try:
                resp = await client.http_session.post(
                    f"{client.base_url}/public-build/vm/{sandbox_info['vm_job_uuid']}/stop-services",
                    json={
                        "dataset": sandbox_info.get("dataset", "base"),
                        "timeout": 600,
                    },
                    headers={"X-API-Key": client.api_key},
                )
                if resp.status == 200:
                    data = await resp.json()
                    correlation_id = data.get("correlation_id")
                    if correlation_id:
                        await _monitor_ssh_execution(
                            client, correlation_id, "Stop services", timeout=180
                        )
                else:
                    err = await resp.text()
                    console.print(f"❌ [red]Failed to stop services: {err}")
            except Exception as e:
                console.print(f"❌ [red]Error stopping services: {e}[/red]")

        elif choice == 7:
            # VS Code via SSH tunnel
            console.print(f"🔧 [cyan]Opening VS Code connected to sandbox...[/cyan]")
            success = _open_editor_via_ssh("code", sandbox_info["ssh_host"], local_port)
            if success:
                console.print("✅ [green]VS Code opened successfully[/green]")
                console.print(
                    "💡 [yellow]Your code is available at /opt/plato in the remote environment[/yellow]"
                )
            else:
                console.print("❌ [red]Failed to open VS Code[/red]")

        elif choice == 8:
            # Cursor via SSH tunnel
            console.print(f"🔧 [cyan]Opening Cursor connected to sandbox...[/cyan]")
            success = _open_editor_via_ssh(
                "cursor", sandbox_info["ssh_host"], local_port
            )
            if success:
                console.print("✅ [green]Cursor opened successfully[/green]")
                console.print(
                    "💡 [yellow]Your code is available at /opt/plato in the remote environment[/yellow]"
                )
            else:
                console.print("❌ [red]Failed to open Cursor[/red]")

        elif choice == 9:
            # Create VM snapshot
            console.print(f"📸 [cyan]Creating VM snapshot...[/cyan]")

            # Get current git commit hash for version
            version = _get_git_commit_hash()
            console.print(f"📝 Using git commit hash as version: {version}")

            # Ask user to confirm dataset
            current_dataset = sandbox_info.get("dataset", "base")
            dataset = typer.prompt(f"Dataset to snapshot", default=current_dataset)

            # Ask for optional snapshot name
            snapshot_name = typer.prompt(
                "Snapshot name (optional, press Enter to skip)", default=""
            )
            if not snapshot_name.strip():
                snapshot_name = None

            try:
                # Read hub config to get service name
                import json
                import os

                config_file = ".plato-hub.json"
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        hub_config = json.load(f)
                    service = hub_config["simulator_name"]
                else:
                    service = typer.prompt("Service name")

                # Prepare snapshot request
                snapshot_request = {
                    "service": service,
                    "version": version,
                    "dataset": dataset,
                    "timeout": 1800,
                }

                if snapshot_name:
                    snapshot_request["snapshot_name"] = snapshot_name

                console.print(f"📋 [cyan]Snapshot details:[/cyan]")
                console.print(f"  • Service: {service}")
                console.print(f"  • Version: {version}")
                console.print(f"  • Dataset: {dataset}")
                if snapshot_name:
                    console.print(f"  • Name: {snapshot_name}")
                console.print(f"  • Timeout: 1800 seconds")

                if not Confirm.ask("Proceed with snapshot creation?", default=True):
                    console.print("🚫 [yellow]Snapshot cancelled[/yellow]")
                    continue

                # Send snapshot request
                snapshot_response = await client.http_session.post(
                    f"{client.base_url}/public-build/vm/{sandbox_info['vm_job_uuid']}/snapshot",
                    json=snapshot_request,
                    headers={"X-API-Key": client.api_key},
                )

                if snapshot_response.status == 200:
                    response_data = await snapshot_response.json()
                    console.print(
                        "✅ [green]Snapshot request submitted successfully[/green]"
                    )

                    # Extract correlation_id for SSE monitoring
                    correlation_id = response_data.get("correlation_id")
                    if correlation_id:
                        # Wait for completion using SSE monitoring
                        success = await _wait_for_snapshot_completion(
                            client, correlation_id, timeout=1800
                        )

                        if success:
                            console.print(
                                "🎉 [green]Snapshot created successfully![/green]"
                            )
                        else:
                            console.print(
                                "❌ [red]Snapshot creation failed or timed out[/red]"
                            )
                    else:
                        console.print(
                            "❌ [red]No correlation_id received from snapshot response[/red]"
                        )

                else:
                    error = await snapshot_response.text()
                    console.print(f"❌ [red]Failed to create snapshot: {error}[/red]")

            except Exception as e:
                console.print(f"❌ [red]Error creating snapshot: {e}[/red]")

        elif choice == 10:
            # Show VM info
            try:
                status_response = await client.get_job_status(
                    sandbox_info["vm_job_uuid"]
                )
                console.print("📊 Sandbox VM Information:")
                console.print(f"  🆔 Job UUID: {sandbox_info['vm_job_uuid']}")
                console.print(
                    f"  📈 Status: {status_response.get('status', 'unknown')}"
                )
                console.print(f"  🔗 SSH: ssh {sandbox_info['ssh_host']}")
                console.print(f"  🔑 SSH key authentication (passwordless)")
                console.print(f"  📁 Code directory: /opt/plato")
                console.print(f"  🌿 Development branch: {sandbox_info['dev_branch']}")
                console.print(f"  💻 VM URL: {sandbox_info['vm_url']}")

                # Show chisel connection info
                console.print(f"  🔗 Chisel tunnel: localhost:{local_port} → VM:22")

                if "message" in status_response:
                    console.print(f"  📝 Status message: {status_response['message']}")

            except Exception as e:
                console.print(f"[red]❌ Failed to get VM status: {e}")

        elif choice == 11:
            # Stop and cleanup
            break
        elif choice == 6:
            # Listeners - Backup (maps to environment backup)
            console.print(f"📦 [cyan] Getting job group id for backup...[/cyan]")
            job_group_id = None
            try:
                job = await client.http_session.get(
                    f"{client.base_url}/jobs/{sandbox_info['vm_job_uuid']}",
                    headers={"X-API-Key": client.api_key},
                )
                job_json = await job.json()
                job_group_id = job_json["job_group_id"]
            except Exception as e:
                console.print(f"[red]❌ Failed to get job group id: {e}")
                break

            console.print("📦 [cyan]Creating environment backup...[/cyan]")
            try:
                backup_response = await client.http_session.post(
                    f"{client.base_url}/env/{job_group_id}/backup",
                    headers={"X-API-Key": client.api_key},
                )

                if backup_response.status == 200:
                    backup_response_json = await backup_response.json()

                    console.print(
                        f"✅ [green]Environment backup completed successfully[/green] {backup_response_json}"
                    )
                else:
                    error = await backup_response.text()
                    console.print(
                        f"❌ [red]Failed to backup environment: {error}[/red]"
                    )

            except Exception as e:
                console.print(f"❌ [red]Error creating environment backup: {e}[/red]")
        elif choice == 5:
            # Listeners - Reset (maps to environment reset)
            console.print(f"📦 [cyan] Getting job group id for reset...[/cyan]")
            job_group_id = None
            try:
                job = await client.http_session.get(
                    f"{client.base_url}/jobs/{sandbox_info['vm_job_uuid']}",
                    headers={"X-API-Key": client.api_key},
                )
                job_json = await job.json()
                job_group_id = job_json["job_group_id"]
            except Exception as e:
                console.print(f"[red]❌ Failed to get job group id: {e}")
                break

            console.print("📦 [cyan]Creating environment reset...[/cyan]")
            try:
                reset_response = await client.http_session.post(
                    f"{client.base_url}/env/{job_group_id}/reset",
                    headers={"X-API-Key": client.api_key},
                    json={"load_browser_state": False},
                )

                if reset_response.status == 200:
                    reset_response_json = await reset_response.json()

                    console.print(
                        f"✅ [green]Environment reset completed successfully[/green] {reset_response_json}"
                    )
                else:
                    error = await reset_response.text()
                    console.print(f"❌ [red]Failed to reset environment: {error}[/red]")

            except Exception as e:
                console.print(f"❌ [red]Error creating environment reset: {e}[/red]")
        elif choice == 12:
            # Start All
            console.print("🚀 [cyan]Starting listeners and services...[/cyan]")
            try:
                # Start listeners
                resp1 = await client.http_session.post(
                    f"{client.base_url}/public-build/vm/{sandbox_info['vm_job_uuid']}/start-listeners",
                    json={
                        "dataset": sandbox_info.get("dataset", "base"),
                        "plato_config": sandbox_info.get("plato_config", {}),
                        "plato_worker_version": None,
                        "timeout": 600,
                    },
                    headers={"X-API-Key": client.api_key},
                )
                if resp1.status == 200:
                    data1 = await resp1.json()
                    cid1 = data1.get("correlation_id")
                    if cid1:
                        await _monitor_ssh_execution(
                            client, cid1, "Start listeners", timeout=180
                        )
                # Start services
                resp2 = await client.http_session.post(
                    f"{client.base_url}/public-build/vm/{sandbox_info['vm_job_uuid']}/start-services",
                    json={
                        "dataset": sandbox_info.get("dataset", "base"),
                        "plato_config": sandbox_info.get("plato_config", {}),
                        "timeout": 600,
                    },
                    headers={"X-API-Key": client.api_key},
                )
                if resp2.status == 200:
                    data2 = await resp2.json()
                    cid2 = data2.get("correlation_id")
                    if cid2:
                        await _monitor_ssh_execution(
                            client, cid2, "Start services", timeout=300
                        )
                console.print("✅ [green]Start All completed[/green]")
            except Exception as e:
                console.print(f"❌ [red]Start All failed: {e}")
        else:
            console.print("❌ Invalid choice. Please enter 1-12.")


def _get_git_commit_hash() -> str:
    """Get the current git commit hash."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()  # Return full hash
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


async def _wait_for_snapshot_completion(
    client: "Plato", correlation_id: str, timeout: int = 1800
) -> bool:
    """Wait for VM snapshot to complete using SSE monitoring."""
    console.print(
        f"🔗 Monitoring via SSE: {client.base_url}/public-build/events/{correlation_id}"
    )

    # Use the existing SSE monitoring infrastructure
    success = await _monitor_ssh_execution(
        client, correlation_id, "VM snapshot creation", timeout=timeout
    )

    return success


async def _setup_chisel_client(ssh_url: str) -> Optional[int]:
    """Setup local chisel client and return the local SSH port"""
    import subprocess
    import random
    import time

    try:
        # Install chisel client if needed
        chisel_path = shutil.which("chisel")
        if not chisel_path:
            console.print("📦 Installing chisel client...")
            # Try to install chisel
            try:
                subprocess.run(
                    [
                        "curl",
                        "-L",
                        "https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_linux_amd64.gz",
                        "-o",
                        "/tmp/chisel.gz",
                    ],
                    check=True,
                    capture_output=True,
                )

                subprocess.run(
                    ["gunzip", "/tmp/chisel.gz"], check=True, capture_output=True
                )
                subprocess.run(
                    ["chmod", "+x", "/tmp/chisel"], check=True, capture_output=True
                )
                subprocess.run(
                    ["sudo", "mv", "/tmp/chisel", "/usr/local/bin/chisel"],
                    check=True,
                    capture_output=True,
                )
                console.print("✅ Chisel installed successfully")
            except subprocess.CalledProcessError:
                console.print("❌ Failed to install chisel. Please install manually.")
                return None
            except FileNotFoundError:
                console.print("❌ curl not found. Please install chisel manually.")
                return None

        # Parse the SSH URL to get server details
        # ssh_url format: https://domain.com/connect-job/job_uuid/chisel_port
        if "/connect-job/" not in ssh_url:
            console.print(f"[red]❌ Invalid SSH URL format: {ssh_url}")
            return None

        url_parts = ssh_url.split("/connect-job/")
        base_url = url_parts[0].replace("https://", "").replace("http://", "")
        job_path = url_parts[1]  # job_uuid/chisel_port

        # Extract server and port for chisel
        server_url = f"{base_url}"
        if "localhost" in base_url:
            server_url = server_url.replace(
                "localhost", "127.0.0.1"
            )  # chisel works better with IP

        # Generate random local port for SSH tunneling
        local_ssh_port = random.randint(2200, 2299)

        # Start chisel client for SSH tunneling (22:127.0.0.1:22 means tunnel port 22 to VM's port 22)
        chisel_cmd = [
            "chisel",
            "client",
            ssh_url,
            f"{local_ssh_port}:127.0.0.1:22",
        ]

        # Show chisel connection panel
        chisel_panel = Panel.fit(
            f"[cyan]Establishing secure tunnel connection...[/cyan]\n"
            f"[dim]Command: {' '.join(chisel_cmd)}[/dim]",
            title="[bold cyan]🔗 Network Tunnel Setup[/bold cyan]",
            border_style="cyan",
        )
        console.print(chisel_panel)

        # Start chisel in background
        chisel_process = subprocess.Popen(
            chisel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Wait a moment for chisel to establish connection
        time.sleep(3)

        # Check if chisel is still running
        if chisel_process.poll() is None:
            # Show tunnel success panel
            tunnel_panel = Panel.fit(
                f"[green]Secure tunnel established successfully![/green]\n"
                f"[cyan]Local SSH port:[/cyan] [bold]{local_ssh_port}[/bold]\n"
                f"[dim]Your local machine can now connect securely to the remote sandbox[/dim]",
                title="[bold green]✅ Tunnel Active[/bold green]",
                border_style="green",
            )
            console.print(tunnel_panel)

            return local_ssh_port
        else:
            stdout, stderr = chisel_process.communicate()
            console.print(f"[red]❌ Chisel client failed: {stderr.decode()}")
            return None

    except Exception as e:
        console.print(f"[red]❌ Error setting up chisel: {e}")
        return None


def _setup_ssh_config_with_password(local_port: int, vm_job_uuid: str):
    """Setup SSH config with SSH key authentication for sandbox"""
    import os

    try:
        ssh_config_dir = os.path.expanduser("~/.ssh")
        os.makedirs(ssh_config_dir, exist_ok=True)

        # Get the path to our SSH key
        key_path = os.path.join(ssh_config_dir, "plato_sandbox_key")

        # Create unique SSH host name with job UUID
        ssh_host = f"plato-sandbox-{vm_job_uuid[:8]}"

        # Create SSH config entry with key authentication
        config_entry = f"""
Host {ssh_host}
    HostName localhost
    Port {local_port}
    User root
    IdentityFile {key_path}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ConnectTimeout 10

"""

        ssh_config_path = os.path.join(ssh_config_dir, "config")

        # Read existing config
        existing_config = ""
        if os.path.exists(ssh_config_path):
            with open(ssh_config_path, "r") as f:
                existing_config = f.read()

        # Remove any existing entry for this specific host
        if f"Host {ssh_host}" in existing_config:
            lines = existing_config.split("\n")
            new_lines = []
            skip_block = False

            for line in lines:
                if line.strip() == f"Host {ssh_host}":
                    skip_block = True
                    continue
                elif line.startswith("Host ") and skip_block:
                    skip_block = False
                    new_lines.append(line)
                elif not skip_block:
                    new_lines.append(line)

            existing_config = "\n".join(new_lines)

        # Add new config
        with open(ssh_config_path, "w") as f:
            f.write(existing_config.rstrip())
            if existing_config and not existing_config.endswith("\n"):
                f.write("\n")
            f.write(config_entry)

        # Show SSH config success panel
        ssh_success_panel = Panel.fit(
            f"[green]SSH configuration updated successfully![/green]\n"
            f"[cyan]Connection command:[/cyan] [bold]ssh {ssh_host}[/bold]\n"
            f"[yellow]🔑 Uses SSH key authentication (passwordless)[/yellow]\n"
            f"[blue]📁 Remote path: /opt/plato[/blue]",
            title="[bold green]✅ SSH Ready[/bold green]",
            border_style="green",
        )
        console.print(ssh_success_panel)

        return ssh_host

    except Exception as e:
        console.print(f"[red]❌ Failed to setup SSH config: {e}")
        return None


def _open_editor_via_ssh(editor: str, ssh_host: str, local_port: int) -> bool:
    """Open editor with simple SSH connection"""
    import subprocess

    try:
        if editor == "code":
            subprocess.run(
                ["code", "--remote", f"ssh-remote+{ssh_host}", "/opt/plato"],
                check=False,
            )
            console.print(
                f"💡 If connection fails, use: F1 → 'Remote-SSH: Connect to Host' → '{ssh_host}'"
            )
        elif editor == "cursor":
            subprocess.run(
                ["cursor", "--remote", f"ssh-remote+{ssh_host}", "/opt/plato"],
                check=False,
            )
            console.print(
                f"💡 If connection fails, use: F1 → 'Remote-SSH: Connect to Host' → '{ssh_host}'"
            )

        return True

    except FileNotFoundError:
        console.print(f"[red]❌ {editor} not found. Please install {editor}.")
        console.print(f"💡 Alternative: ssh {ssh_host} (SSH key authentication)")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error opening {editor}: {e}")
        return False


def _hub_status(hub_config: dict, command: str, extra_args: list):
    """Show git status for the hub-linked directory in isolation"""
    import tempfile
    import subprocess
    import shutil

    try:
        clone_url = _get_authenticated_url(hub_config)
        if not clone_url:
            # For read-only commands, try without auth first
            clone_url = hub_config["repository"]["clone_url"]

        sim_name = hub_config["simulator_name"]

        # Create temporary directory for isolated git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, "temp_repo")
            current_dir = os.getcwd()

            # Try to clone the simulator repository first to get the baseline
            clone_result = subprocess.run(
                ["git", "clone", clone_url, temp_repo], capture_output=True, text=True
            )

            if clone_result.returncode != 0:
                # If clone fails (auth issues, empty repo, etc), create fresh repo
                subprocess.run(
                    ["git", "init", "--initial-branch=main", temp_repo],
                    capture_output=True,
                    check=True,
                )
                console.print(
                    f"📁 Creating isolated view (couldn't fetch remote: {clone_result.stderr.strip()[:50]}...)"
                )
            else:
                console.print(f"📡 Comparing against simulator repository")

            # Copy current directory contents over the cloned/initialized repo
            os.chdir(temp_repo)

            # Remove all files except .git to replace with current directory content
            for item in os.listdir("."):
                if not item.startswith(".git"):
                    item_path = os.path.join(".", item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)

            # Copy current directory contents
            for item in os.listdir(current_dir):
                if item.startswith(".git") or item == ".plato-hub.json":
                    continue  # Skip git and config files

                src = os.path.join(current_dir, item)
                dst = os.path.join(".", item)

                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst)

            # Run the requested command
            git_cmd = ["git", command] + extra_args
            result = subprocess.run(git_cmd, capture_output=False, text=True)

    except Exception as e:
        console.print(f"[red]❌ Error during {command}: {e}")


def _get_authenticated_url(hub_config: dict) -> Optional[str]:
    """Get authenticated clone URL using cached credentials"""
    import os
    import json

    # Check for cached credentials
    cache_dir = os.path.expanduser("~/.plato-hub")
    cache_file = os.path.join(cache_dir, "credentials.json")

    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, "r") as f:
            credentials = json.load(f)

        base_url = hub_config["repository"]["clone_url"]
        username = credentials.get("username")
        password = credentials.get("password")

        if username and password and base_url.startswith("https://"):
            return base_url.replace("https://", f"https://{username}:{password}@")

    except Exception:
        pass

    return None


def _ensure_gitignore_protects_credentials():
    """Add credential files to .gitignore if not already present"""
    import subprocess

    try:
        # Check if we're in a git repository
        result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True)
        if result.returncode != 0:
            return  # Not in a git repo, nothing to do

        # Get git root directory
        root_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
        if root_result.returncode != 0:
            return

        git_root = root_result.stdout.strip()
        gitignore_path = os.path.join(git_root, ".gitignore")

        # Patterns to protect
        protect_patterns = [
            "# Plato hub credentials",
            "credentials.json",
            ".plato-hub/",
            "*.plato-hub.json",
        ]

        # Read existing gitignore
        existing_content = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                existing_content = f.read()

        # Check which patterns need to be added
        patterns_to_add = []
        for pattern in protect_patterns:
            if pattern not in existing_content:
                patterns_to_add.append(pattern)

        # Add missing patterns
        if patterns_to_add:
            with open(gitignore_path, "a") as f:
                if existing_content and not existing_content.endswith("\n"):
                    f.write("\n")
                f.write("\n".join(patterns_to_add) + "\n")

            console.print(
                f"✅ Added {len(patterns_to_add)} credential protection patterns to .gitignore",
            )

    except Exception as e:
        # Silently fail - gitignore protection is nice-to-have, not critical
        pass


# Hub commands for Git repository management
hub_app = typer.Typer(
    help="[bold purple]Plato Hub[/bold purple] - Manage simulator repositories and development environments."
)
app.add_typer(hub_app, name="hub")


@hub_app.command()
def init(
    sim_name: str = typer.Argument(..., help="The name of the new simulator to create"),
    description: Optional[str] = typer.Option(
        None, help="Description for the new simulator"
    ),
    sim_type: str = typer.Option("docker_app", "--sim-type", help="Type of simulator"),
    directory: Optional[str] = typer.Option(
        None, help="Directory to create and clone into (default: sim_name)"
    ),
):
    """
    [bold green]Initialize a new simulator with repository and clone it.[/bold green]

    Creates a new simulator, sets up its repository, and clones it to your local machine.
    """

    async def _init():
        client = Plato()
        try:
            # Check if simulator already exists
            with console.status(
                "[bold blue]Checking existing simulators...", spinner="dots"
            ):
                existing_simulators = await client.list_gitea_simulators()

            for sim in existing_simulators:
                if sim["name"].lower() == sim_name.lower():
                    console.print(
                        f"[red]❌ Simulator '{sim_name}' already exists[/red]"
                    )
                    raise typer.Exit(1)

            # Step 1: Create the simulator
            with console.status(
                f"[bold green]Creating simulator '{sim_name}'...", spinner="dots"
            ):
                simulator = await client.create_simulator(
                    name=sim_name, description=description, sim_type=sim_type
                )

            console.print(
                f"[green]✅ Created simulator: {simulator['name']} (ID: {simulator['id']})[/green]"
            )

            # Step 2: Create repository for the simulator
            with console.status("[bold blue]Creating repository...", spinner="dots"):
                repo_info = await client.create_simulator_repository(simulator["id"])

            console.print(
                f"[green]✅ Created repository: {repo_info['full_name']}[/green]"
            )

            # Step 3: Clone the repository
            target_dir = directory or sim_name

            # Get authenticated clone URL
            creds = await client.get_gitea_credentials()
            clone_url = repo_info["clone_url"]
            if clone_url.startswith("https://"):
                authenticated_url = clone_url.replace(
                    "https://", f"https://{creds['username']}:{creds['password']}@"
                )
                clone_url = authenticated_url

            import subprocess

            try:
                with console.status(
                    f"[bold cyan]Cloning {repo_info['full_name']} to {target_dir}...",
                    spinner="dots",
                ):
                    result = subprocess.run(
                        ["git", "clone", clone_url, target_dir],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                # Success panel
                success_panel = Panel.fit(
                    f"[green]Simulator '{sim_name}' is ready![/green]\\n"
                    f"[cyan]📁 Directory:[/cyan] [bold]{target_dir}[/bold]\\n"
                    f"[cyan]💡 Next step:[/cyan] cd {target_dir} && start developing"
                    + (
                        f"\\n[cyan]📝 Description:[/cyan] {repo_info['description']}"
                        if repo_info.get("description")
                        else ""
                    ),
                    title="[bold green]🎉 Initialization Complete[/bold green]",
                    border_style="green",
                )
                console.print(success_panel)

            except subprocess.CalledProcessError as e:
                console.print(
                    f"[red]❌ Failed to clone repository: {e.stderr.strip()}[/red]"
                )
                raise typer.Exit(1)
            except FileNotFoundError:
                console.print("[red]❌ Git is not installed or not in PATH[/red]")
                raise typer.Exit(1)

        except Exception as e:
            console.print(f"[red]❌ Initialization failed: {e}[/red]")
            raise typer.Exit(1)
        finally:
            await client.close()

    handle_async(_init())


@hub_app.command()
def clone(
    sim_name: str = typer.Argument(
        ..., help="The name of the simulator to clone (e.g., 'espocrm', 'doordash')"
    ),
    directory: Optional[str] = typer.Option(
        None, "--directory", help="Directory to clone into (default: current directory)"
    ),
):
    """
    [bold blue]Clone a simulator repository.[/bold blue]

    Downloads and sets up a local copy of the specified simulator.
    """

    async def _clone():
        client = Plato()
        try:
            console.print(f"Looking up simulator '{sim_name}'...")

            # Get all available simulators
            simulators = await client.list_gitea_simulators()

            # Find the simulator by name
            simulator = None
            for sim in simulators:
                if sim["name"].lower() == sim_name.lower():
                    simulator = sim
                    break

            if not simulator:
                console.print(f"[red]❌ Simulator '{sim_name}' not found.")
                available = [s["name"] for s in simulators]
                if available:
                    console.print(f"💡 Available simulators: {', '.join(available)}")
                return

            if not simulator.get("has_repo", False):
                console.print(
                    f"❌ Simulator '{sim_name}' exists but doesn't have a repository configured.",
                )
                console.print(
                    "💡 Contact your administrator to set up a repository for this simulator.",
                )
                return

            # Get repository details
            repo_info = await client.get_simulator_repository(simulator["id"])
            if not repo_info.get("has_repo", False):
                console.print(
                    f"❌ Repository for simulator '{sim_name}' is not available.",
                )
                console.print(f"💡 Attempting to create repository for '{sim_name}'...")

                # Try to create the repository
                try:
                    create_response = await client.http_session.post(
                        f"{client.base_url}/gitea/simulators/{simulator['id']}/repo",
                        headers={"X-API-Key": client.api_key},
                    )
                    if create_response.status == 200:
                        repo_info = await create_response.json()
                        console.print(f"[green]✅ Created repository for '{sim_name}'")
                    else:
                        error_text = await create_response.text()
                        console.print(f"❌ Failed to create repository: {error_text}")
                        return
                except Exception as create_e:
                    console.print(f"[red]❌ Failed to create repository: {create_e}")
                    return

            clone_url = repo_info["clone_url"]
            repo_name = repo_info["name"]

            # Get cached credentials (same as other hub git operations)
            hub_config_for_auth = {"repository": {"clone_url": clone_url}}
            authenticated_clone_url = _get_authenticated_url(hub_config_for_auth)

            if authenticated_clone_url:
                clone_url = authenticated_clone_url
                console.print("✅ Using cached credentials for authentication")
            else:
                console.print(
                    "⚠️  No cached credentials found. Run 'uv run plato hub login' first."
                )
                return

            # Determine target directory
            if directory:
                target_dir = directory
            else:
                target_dir = repo_name

            console.print(f"Cloning {repo_info['full_name']} to {target_dir}...")

            # Clone the repository
            import subprocess
            import json

            try:
                result = subprocess.run(
                    ["git", "clone", clone_url, target_dir],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                console.print(f"[green]✅ Successfully cloned {repo_info['full_name']}")
                console.print(f"Repository cloned to: {target_dir}")

                # Create .plato-hub.json configuration in the cloned directory
                try:
                    hub_config = {
                        "simulator_name": sim_name,
                        "simulator_id": simulator["id"],
                        "repository": {
                            "name": repo_info["name"],
                            "full_name": repo_info["full_name"],
                            "clone_url": repo_info["clone_url"]
                            .replace("https://", "https://")
                            .split("@")[-1]
                            if "@" in repo_info["clone_url"]
                            else repo_info["clone_url"],  # Strip any embedded auth
                            "description": repo_info.get("description"),
                        },
                        "sync_directory": os.path.basename(target_dir),
                    }

                    config_path = os.path.join(target_dir, ".plato-hub.json")
                    with open(config_path, "w") as f:
                        json.dump(hub_config, f, indent=2)

                    console.print("✅ Created Plato hub configuration")
                    console.print(
                        "💡 You can now use 'uv run plato hub sandbox' in this directory"
                    )

                except Exception as config_e:
                    console.print(
                        f"⚠️  Warning: Could not create hub config: {config_e}"
                    )

                if repo_info.get("description"):
                    console.print(f"Description: {repo_info['description']}")

            except subprocess.CalledProcessError as e:
                console.print(f"❌ Failed to clone repository: {e.stderr.strip()}")
                if "Authentication failed" in e.stderr:
                    console.print("🔧 Try running: uv run plato hub login")
                    console.print(
                        "💡 Or check if the repository exists and you have access to it"
                    )
            except FileNotFoundError:
                console.print("❌ Git is not installed or not in PATH")

        finally:
            await client.close()

    handle_async(_clone())


@hub_app.command()
def link(
    sim_name: str = typer.Argument(..., help="The name of the simulator to link to"),
    directory: Optional[str] = typer.Argument(
        None, help="Directory to link (default: current directory)"
    ),
):
    """
    [bold cyan]Link a local directory to a simulator repository.[/bold cyan]

    Sets up git remote without cloning - useful for monorepos.
    """

    async def _link():
        client = Plato()
        try:
            import os
            import subprocess

            # Determine target directory
            target_dir = directory or os.getcwd()

            console.print(f"Looking up simulator '{sim_name}'...")

            # Get all available simulators
            simulators = await client.list_gitea_simulators()

            # Find the simulator by name
            simulator = None
            for sim in simulators:
                if sim["name"].lower() == sim_name.lower():
                    simulator = sim
                    break

            if not simulator:
                console.print(f"[red]❌ Simulator '{sim_name}' not found.")
                available = [s["name"] for s in simulators]
                if available:
                    console.print(f"💡 Available simulators: {', '.join(available)}")
                return

            if not simulator.get("has_repo", False):
                console.print(
                    f"❌ Simulator '{sim_name}' exists but doesn't have a repository configured.",
                )
                console.print(
                    "💡 Contact your administrator to set up a repository for this simulator.",
                )
                return

            # Get repository details
            repo_info = await client.get_simulator_repository(simulator["id"])
            if not repo_info.get("has_repo", False):
                console.print(
                    f"Repository for simulator '{sim_name}' is not available."
                )
                return

            clone_url = repo_info["clone_url"]

            # Use admin credentials if available for authenticated operations
            if repo_info.get("admin_credentials"):
                creds = repo_info["admin_credentials"]
                # Construct authenticated URL: https://username:password@domain/path
                if clone_url.startswith("https://"):
                    # Replace https:// with https://username:password@
                    authenticated_url = clone_url.replace(
                        "https://", f"https://{creds['username']}:{creds['password']}@"
                    )
                    clone_url = authenticated_url
                    console.print(f"Using admin credentials for authentication")

            console.print(
                f"Linking directory '{target_dir}' to {repo_info['full_name']}..."
            )

            # Change to target directory
            original_dir = os.getcwd()
            os.chdir(target_dir)

            try:
                import json

                # Create plato hub configuration file (without credentials)
                hub_config = {
                    "simulator_name": sim_name,
                    "simulator_id": simulator["id"],
                    "repository": {
                        "name": repo_info["name"],
                        "full_name": repo_info["full_name"],
                        "clone_url": repo_info["clone_url"]
                        .replace("https://", "https://")
                        .split("@")[-1]
                        if "@" in repo_info["clone_url"]
                        else repo_info["clone_url"],  # Strip any embedded auth
                        "description": repo_info.get("description"),
                    },
                    "sync_directory": os.path.basename(target_dir),
                }

                # Write config to .plato-hub.json
                config_file = os.path.join(target_dir, ".plato-hub.json")
                with open(config_file, "w") as f:
                    json.dump(hub_config, f, indent=2)

                console.print(
                    f"[green]✅ Created Plato hub configuration for '{sim_name}'"
                )
                console.print(
                    f"🔗 Directory '{target_dir}' is now linked to {repo_info['full_name']}"
                )
                console.print(
                    "💡 This directory will sync with the simulator repo independently"
                )
                console.print("💡 Run 'uv run plato hub login' to authenticate")
                console.print("💡 Then use 'uv run plato hub git push/pull' to sync")
                console.print("💡 Your monorepo structure remains intact!")

            except subprocess.CalledProcessError as e:
                console.print(
                    f"❌ Failed to link repository: {e.stderr.decode().strip()}",
                )
            except FileNotFoundError:
                console.print("❌ Git is not installed or not in PATH")
            finally:
                os.chdir(original_dir)

        finally:
            await client.close()

    handle_async(_link())


@hub_app.command()
def login():
    """Authenticate with Plato hub for git operations."""

    async def _login():
        import os
        import json
        from datetime import datetime

        client = Plato()
        try:
            console.print("🔐 Authenticating with Plato hub...")

            # Get admin credentials from the API
            creds = await client.get_gitea_credentials()

            # Create cache directory
            cache_dir = os.path.expanduser("~/.plato-hub")
            os.makedirs(cache_dir, exist_ok=True)

            # Cache credentials securely
            credentials = {
                "username": creds["username"],
                "password": creds["password"],
                "org_name": creds["org_name"],
                "cached_at": datetime.now().isoformat(),
            }

            # Save credentials to cache
            cache_file = os.path.join(cache_dir, "credentials.json")
            with open(cache_file, "w") as f:
                json.dump(credentials, f, indent=2)

            # Set restrictive permissions on credentials file
            os.chmod(cache_file, 0o600)

            # Add credentials to gitignore for security
            _ensure_gitignore_protects_credentials()

            console.print("✅ Successfully authenticated with Plato hub")
            console.print(f"👤 Username: {creds['username']}")
            console.print(f"🏢 Organization: {creds['org_name']}")
            console.print("💡 Credentials cached securely for git operations")

        except Exception as e:
            console.print(f"[red]❌ Login failed: {e}")
        finally:
            await client.close()

    handle_async(_login())


@hub_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def git(ctx: typer.Context):
    """
    [bold green]Execute git commands with authenticated Plato hub remote.[/bold green]

    Examples:
      uv run plato hub git status
      uv run plato hub git push origin main
      uv run plato hub git pull
    """
    import os
    import subprocess

    # Get the extra arguments from typer context
    args = ctx.args

    if not args:
        console.print("❌ Please provide a git command")
        console.print("[yellow]💡 Example: uv run plato hub git status[/yellow]")
        return

    try:
        import json
        import tempfile
        import shutil

        # Check for .plato-hub.json configuration
        config_file = ".plato-hub.json"
        hub_config = None

        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    hub_config = json.load(f)
                console.print(
                    f"✅ Found Plato hub configuration for '{hub_config['simulator_name']}'",
                )
            except Exception as e:
                console.print(f"[red]❌ Error reading hub config: {e}")
                return

        if not hub_config:
            # Fallback to regular git command
            console.print(
                "⚠️  No Plato hub configuration found. Running regular git command...",
            )
            git_cmd = ["git"] + list(args)
            result = subprocess.run(git_cmd, capture_output=False, text=True)
            if result.returncode != 0:
                raise typer.Exit(result.returncode)
            return

        # Handle Plato hub-specific git operations
        command = args[0] if args else ""

        if command == "push":
            _hub_push(hub_config, list(args[1:]) if len(args) > 1 else [])
        elif command == "pull":
            _hub_pull(hub_config, list(args[1:]) if len(args) > 1 else [])
        elif command in ["status", "log", "diff", "branch"]:
            # For read-only commands, create a temporary isolated view
            _hub_status(hub_config, command, list(args[1:]) if len(args) > 1 else [])
        else:
            # For other commands, run them normally but warn about hub context
            console.print(f"[yellow]⚠️  Running '{command}' in hub-linked directory")
            git_cmd = ["git"] + list(args)
            result = subprocess.run(git_cmd, capture_output=False, text=True)
            if result.returncode != 0:
                raise typer.Exit(result.returncode)

    except FileNotFoundError:
        console.print("❌ Git is not installed or not in PATH")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error executing git command: {e}")
        raise typer.Exit(1)


@hub_app.command()
def sandbox(
    config: str = typer.Option(
        "plato-config.yml", "--config", help="VM configuration file"
    ),
    dataset: str = typer.Option(
        "base", "--dataset", help="Dataset to use for the sandbox"
    ),
    keep_vm: bool = typer.Option(
        False, "--keep-vm", help="Keep VM running after sandbox exits"
    ),
    chisel_port: int = typer.Option(
        6000, "--chisel-port", help="Port for chisel server"
    ),
):
    """
    [bold magenta]Start a development sandbox environment.[/bold magenta]

    Creates a development VM with your simulator code and opens an interactive environment.
    Uses plato-config.yml to configure compute resources, datasets, and mutation listeners.

    Expected plato-config.yml structure:
        compute:
          cpus: 1
          memory: 2048        # MB
          disk: 10240         # MB
          app_port: 8080
          plato_messaging_port: 7000

        datasets:
          base:
            services:
              - type: "docker-compose"
                file: "datasets/base/docker-compose.yml"
            listeners:
              - type: "db"
                db_type: "postgresql"
                db_host: "base-db.internal"
                db_port: 5432
                db_user: "base_user"
                db_password: "${BASE_DB_PASSWORD}"
                db_database: "base_db"
    """

    async def _sandbox():
        import os
        import json
        import yaml
        import uuid
        import subprocess
        import asyncio
        from datetime import datetime

        client = Plato()
        vm_job_uuid = None

        try:
            # Step 1: Check for .plato-hub.json configuration
            config_file = ".plato-hub.json"

            if not os.path.exists(config_file):
                console.print("❌ No Plato hub configuration found in this directory.")
                console.print(
                    "💡 Use 'uv run plato hub clone <sim_name>' or 'uv run plato hub link <sim_name>' first.",
                )
                return

            try:
                with open(config_file, "r") as f:
                    hub_config = json.load(f)

                sim_name = hub_config["simulator_name"]
                console.print(f"[green]✅ Found Plato simulator: {sim_name}")

            except Exception as e:
                console.print(f"[red]❌ Error reading hub config: {e}")
                return

            # Step 2: Load VM configuration from plato-config.yml
            plato_config = None

            if os.path.exists(config):
                try:
                    with open(config, "r") as f:
                        config_data = yaml.safe_load(f)
                    plato_config = PlatoConfig.model_validate(config_data or {})
                    console.print(f"[green]✅ Loaded config from {config}")
                except Exception as e:
                    console.print(f"[yellow]⚠️  Could not load {config}: {e}")
            else:
                # Create default config if it doesn't exist
                console.print(f"[yellow]⚠️  No {config} found in current directory")
                if Confirm.ask(
                    "💡 Would you like to create a default plato-config.yml file?",
                    default=True,
                ):
                    await _create_default_config(config)
                    console.print(f"[green]✅ Created default {config}")
                    try:
                        with open(config, "r") as f:
                            config_data = yaml.safe_load(f)
                        plato_config = PlatoConfig.model_validate(config_data or {})
                    except Exception:
                        pass

            # Create default plato_config if loading failed
            if plato_config is None:
                plato_config = PlatoConfig(
                    compute=ComputeConfig(),
                    datasets={
                        "base": DatasetConfig(
                            services=[
                                DockerComposeServiceConfig(
                                    type="docker-compose",
                                    file="datasets/base/docker-compose.yml",
                                )
                            ],
                            listeners=[],
                        )
                    },
                )
                console.print("[yellow]📋 Using default configuration")

            # Debug: Log outgoing DB listener for selected dataset (redacted)
            try:
                if dataset in plato_config.datasets:
                    ds = plato_config.datasets[dataset]
                    outgoing_db = None
                    for listener in getattr(ds, "listeners", []) or []:
                        if isinstance(listener, DatabaseMutationListenerConfig):
                            ldict = listener.model_dump()
                            if "db_password" in ldict:
                                ldict["db_password"] = "***"
                            outgoing_db = ldict
                            break
                    if outgoing_db:
                        console.print(
                            f"[dim]DEBUG outgoing DB listener for dataset '{dataset}': {outgoing_db}[/dim]"
                        )
            except Exception as e:
                console.print(
                    f"[dim]DEBUG failed to log outgoing DB listener: {e}[/dim]"
                )

            # Show config summary
            compute = plato_config.compute
            console.print(
                f"💻 CPUs: {compute.cpus}, Memory: {compute.memory}MB, Disk: {compute.disk}MB"
            )
            console.print(
                f"🔗 App port: {compute.app_port}, Messaging port: {compute.plato_messaging_port}"
            )
            console.print(f"📊 Dataset: {dataset}")
            if dataset in plato_config.datasets:
                ds = plato_config.datasets[dataset]
                try:
                    svc_summary = ", ".join(
                        [
                            getattr(s, "file", getattr(s, "type", "svc"))
                            for s in getattr(ds, "services", [])
                        ]
                    )
                    if svc_summary:
                        console.print(f"🚀 Services: {svc_summary}")
                except Exception:
                    pass
                try:
                    lst_count = len(getattr(ds, "listeners", []) or [])
                    if lst_count:
                        console.print(f"👂 Listeners: {lst_count} configured")
                except Exception:
                    pass
            else:
                console.print(
                    f"[yellow]⚠️  Dataset '{dataset}' not found, VM will use compute config only"
                )

            # Step 3: Create development branch and push current state
            branch_uuid = str(uuid.uuid4())[:8]
            dev_branch = f"dev-{branch_uuid}"

            console.print(f"🌱 Creating development branch: {dev_branch}")

            # Get authenticated URL
            clone_url = _get_authenticated_url(hub_config)
            if not clone_url:
                console.print(
                    "❌ Authentication required. Run 'uv run plato hub login' first.",
                )
                return

            # Create temp repo to push current state
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                current_dir = os.getcwd()

                # Clone the repository
                subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                os.chdir(temp_repo)

                # Create and checkout development branch
                subprocess.run(
                    ["git", "checkout", "-b", dev_branch],
                    capture_output=True,
                    check=True,
                )

                # Copy current directory contents
                for item in os.listdir(current_dir):
                    if item.startswith(".git") or item == ".plato-hub.json":
                        continue

                    src = os.path.join(current_dir, item)
                    dst = os.path.join(".", item)

                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)

                # Commit and push branch
                subprocess.run(["git", "add", "."], capture_output=True)
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"Development snapshot for sandbox {branch_uuid}",
                    ],
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "push", "origin", dev_branch],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                os.chdir(current_dir)

            console.print(
                f"[green]✅ Created and pushed development branch: {dev_branch}"
            )

            # Step 4: Start VM with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=False,
            ) as progress:
                overall_task = progress.add_task(
                    "[bold blue]🚀 Starting sandbox VM...", total=4
                )
                progress.update(
                    overall_task,
                    advance=1,
                    description="[bold blue]🚀 Creating VM instance...",
                )

            # Create VM
            vm_response = await client.http_session.post(
                f"{client.base_url}/public-build/vm/create",
                json={
                    "service": sim_name,
                    "version": "sandbox",
                    "plato_config": plato_config.model_dump(),
                    "wait_time": 120,
                    "vm_timeout": 1800,
                    "alias": f"{sim_name}-sandbox",
                },
                headers={"X-API-Key": client.api_key},
            )

            if vm_response.status != 200:
                error = await vm_response.text()
                console.print(f"[red]❌ Failed to create VM: {error}")
                return

            vm_info = await vm_response.json()
            vm_job_uuid = vm_info["uuid"]
            correlation_id = vm_info["correlation_id"]

            console.print(f"[green]✅ VM created: {vm_job_uuid}")
            console.print(f"🔗 URL: {vm_info['url']}")
            console.print(f"⏳ Waiting for VM to start...")

            # Wait for VM to be ready by monitoring SSE stream
            vm_ready = await _wait_for_vm_ready(client, correlation_id)

            if not vm_ready:
                console.print("❌ VM failed to start properly")
                return

            console.print(f"[green]✅ VM is ready!")

            # Step 5: Setup sandbox environment
            console.print(f"🔧 Setting up sandbox environment...")

            setup_response = await _setup_sandbox(
                client, vm_job_uuid, dev_branch, clone_url, chisel_port
            )

            if not setup_response:
                console.print("❌ Failed to setup sandbox environment")
                return

            ssh_url = setup_response["ssh_url"]
            correlation_id = setup_response["correlation_id"]

            # Wait for sandbox setup to complete
            console.print(f"⏳ Setting up sandbox environment...")
            setup_success = await _wait_for_setup_ready(client, correlation_id)

            if not setup_success:
                console.print(
                    "❌ Sandbox setup failed - check the error messages above for details",
                )
                # VM was created but setup failed, still cleanup if not keeping VM
                if not keep_vm:
                    try:
                        await client.http_session.delete(
                            f"{client.base_url}/public-build/vm/{vm_job_uuid}",
                            headers={"X-API-Key": client.api_key},
                        )
                        console.print("🧹 Cleaned up failed VM")
                    except:
                        pass
                return

            # Show final success panel with all details
            final_panel = Panel(
                f"[green]🎉 Your development sandbox is now fully operational![/green]\n\n"
                f"[bold cyan]Connection Details:[/bold cyan]\n"
                f"[cyan]• SSH URL:[/cyan] {ssh_url}\n"
                f"[cyan]• Code location:[/cyan] [bold]/opt/plato[/bold]\n"
                f"[cyan]• Development branch:[/cyan] [bold]{dev_branch}[/bold]\n\n"
                f"[yellow]✨ Ready for development! Choose your next action below.[/yellow]",
                title="[bold green]🚀 Sandbox Ready[/bold green]",
                border_style="green",
            )
            console.print(final_panel)

            # Step 6: Interactive sandbox mode
            sandbox_info = {
                "vm_job_uuid": vm_job_uuid,
                "dev_branch": dev_branch,
                "vm_url": vm_info["url"],
                "ssh_url": ssh_url,
                "chisel_port": chisel_port,
                "dataset": dataset,
                "plato_config": plato_config.model_dump(),
            }
            await _run_interactive_sandbox(sandbox_info, client, keep_vm)

        except KeyboardInterrupt:
            console.print("\n🛑 Sandbox interrupted by user")
        except Exception as e:
            console.print(f"[red]❌ Sandbox failed: {e}")
        finally:
            # Cleanup VM unless keep_vm is specified
            if vm_job_uuid and not keep_vm:
                try:
                    console.print("🧹 Cleaning up VM...")
                    await client.http_session.delete(
                        f"{client.base_url}/public-build/vm/{vm_job_uuid}",
                        headers={"X-API-Key": client.api_key},
                    )
                    console.print("✅ VM cleaned up")
                except Exception as cleanup_e:
                    console.print(f"[yellow]⚠️  Failed to cleanup VM: {cleanup_e}")
            elif keep_vm:
                console.print(
                    f"💡 VM {vm_job_uuid} is still running (use --keep-vm flag was used)"
                )

            await client.close()

    handle_async(_sandbox())


def main():
    """Main entry point for the Plato CLI."""
    app()


# Backward compatibility alias for entry points
cli = main

if __name__ == "__main__":
    main()
