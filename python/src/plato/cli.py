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
from rich.prompt import Confirm

from plato.sdk import Plato
from plato.hub import Hub
from plato.sandbox import Sandbox
from dotenv import load_dotenv


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


@hub_app.command()
def sandbox(
    config: str = typer.Option(
        "plato-config.yml", "--config", help="VM configuration file"
    ),
    dataset: str = typer.Option("base", "--dataset", help="Dataset to use"),
    chisel_port: int = typer.Option(6000, "--chisel-port", help="Chisel server port"),
):
    """Start a development sandbox environment."""

    async def _sandbox():
        sdk = Plato()

        try:
            # Initialize sandbox service (async init)
            sandbox_service = Sandbox()
            await sandbox_service.init(console, dataset, sdk, chisel_port)

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
        menu_table.add_row("0", "Exit and cleanup")
        menu_table.add_row("1", "Start Services")
        menu_table.add_row("2", "Start Listeners")
        menu_table.add_row("4", "Create VM snapshot")
        menu_table.add_row("7", "Sim Backup")
        menu_table.add_row("8", "Sim Reset")

        console.print("\n")
        console.print(menu_table)

        try:
            raw = input("Choose an action (0/1/2/4/7/8 or q to quit): ")
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
            break
        elif choice == 1:
            await handle_start_services(sandbox)
        elif choice == 2:
            await handle_start_listeners(sandbox)
        elif choice == 4:
            await handle_create_snapshot(sandbox)
        elif choice == 7:
            await handle_sim_backup(sandbox)
        elif choice == 8:
            await handle_sim_reset(sandbox)
        else:
            console.print("[red]❌ Invalid choice. Please enter 0/1/2/3/4/5/7/8.[/red]")


async def handle_create_snapshot(sandbox: Sandbox):
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return
    """Handle snapshot creation."""
    console.print("[cyan]📸 Creating VM snapshot...[/cyan]")

    # Get snapshot details from user matching service API
    try:
        service = typer.prompt(
            "Service name (e.g., plato-service/app_sims/<name>)",
            default=sandbox.sandbox_info.service,
        )
        version = typer.prompt(
            "Version (branch)", default=sandbox.sandbox_info.dev_branch
        )
        dataset = typer.prompt(
            "Dataset to snapshot", default=sandbox.sandbox_info.dataset
        )
        snapshot_name = typer.prompt(
            "Snapshot name (optional, press Enter to skip)", default=""
        )
    except (KeyboardInterrupt, typer.Abort, EOFError):
        # Bubble up to caller to exit entire sandbox
        raise

    if not snapshot_name.strip():
        snapshot_name = None

    # Execute snapshot
    await sandbox.snapshot(
        service=f"{service}",
        version=version,
        dataset=dataset,
        snapshot_name=snapshot_name or "",
    )
    console.print("[green]✅ Snapshot request submitted[/green]")


async def handle_sim_backup(sandbox: Sandbox):
    """Handle simulator backup."""
    console.print("[cyan]💾 Creating simulator backup...[/cyan]")

    try:
        await sandbox.backup()
    except Exception as e:
        console.print(f"[red]❌ Error creating backup: {e}[/red]")


async def handle_sim_reset(sandbox: Sandbox):
    """Handle simulator reset."""
    console.print("[cyan]🔄 Resetting simulator environment...[/cyan]")

    try:
        await sandbox.reset()
    except Exception as e:
        console.print(f"[red]❌ Error resetting simulator: {e}[/red]")


async def handle_start_services(sandbox: Sandbox):
    """Handle starting simulator services."""
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    console.print("[cyan]🚀 Starting simulator services...[/cyan]")

    # Get dataset from user (default to the one used in sandbox)
    try:
        dataset = typer.prompt("Dataset to use", default=sandbox.sandbox_info.dataset)
    except (KeyboardInterrupt, typer.Abort, EOFError):
        # Bubble up to caller to exit entire sandbox
        raise

    try:
        # Get timeout from service configuration, defaulting to a reasonable value
        service_timeout = 900  # Default 15 minutes
        if (sandbox.sandbox_info and
            hasattr(sandbox.sandbox_info, 'dataset_config') and
            sandbox.sandbox_info.dataset_config.services):
            # Get the timeout from the main service (typically main_app)
            main_service = None
            for service_name, service_config in sandbox.sandbox_info.dataset_config.services.items():
                if 'main' in service_name.lower() or service_name == 'main_app':
                    main_service = service_config
                    break
            if not main_service and sandbox.sandbox_info.dataset_config.services:
                # Fall back to first service if no main service found
                main_service = next(iter(sandbox.sandbox_info.dataset_config.services.values()))

            if main_service and hasattr(main_service, 'healthy_wait_timeout'):
                service_timeout = main_service.healthy_wait_timeout

        await sandbox.start_services(dataset=dataset, timeout=service_timeout)
    except Exception as e:
        console.print(f"[red]❌ Error starting services: {e}[/red]")


async def handle_start_listeners(sandbox: Sandbox):
    """Handle starting listeners and worker."""
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    console.print("[cyan]🎧 Starting listeners and worker...[/cyan]")

    # Get configuration from user
    try:
        dataset = typer.prompt("Dataset to use", default=sandbox.sandbox_info.dataset)
    except (KeyboardInterrupt, typer.Abort, EOFError):
        # Bubble up to caller to exit entire sandbox
        raise

    try:
        await sandbox.start_listeners(dataset=dataset)
    except Exception as e:
        console.print(f"[red]❌ Error starting listeners: {e}[/red]")


def main():
    """Main entry point for the Plato CLI."""
    app()


# Backward compatibility
cli = main

if __name__ == "__main__":
    main()
