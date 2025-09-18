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
            console.print("[red]❌ Invalid choice. Please enter 0/1/2/4/7/8.[/red]")


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
        service=service,
        version=version,
        dataset=dataset,
        snapshot_name=snapshot_name or "",
    )
    console.print("[green]✅ Snapshot request submitted[/green]")


async def handle_sim_backup(sandbox: Sandbox):
    """Handle simulator backup."""
    console.print("[cyan]💾 Creating simulator backup...[/cyan]")

    try:
        result = await sandbox.backup()
        if result.success:
            console.print("[green]✅ Backup created successfully[/green]")
        else:
            console.print(f"[red]❌ Backup failed: {result.error}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error creating backup: {e}[/red]")


async def handle_sim_reset(sandbox: Sandbox):
    """Handle simulator reset."""
    console.print("[cyan]🔄 Resetting simulator environment...[/cyan]")

    try:
        result = await sandbox.reset()
        if result.success:
            console.print("[green]✅ Simulator reset successfully[/green]")
        else:
            console.print(f"[red]❌ Reset failed: {result.error}[/red]")
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
        await sandbox.start_services(dataset=dataset)
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
