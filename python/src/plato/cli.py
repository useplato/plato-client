#!/usr/bin/env python3
"""
Plato CLI - Command line interface for Plato services

This CLI orchestrates the various Plato services:
- Hub Service: Repository and project management
- Sandbox Service: Development environment management
- SDK: Core API communication

The CLI handles user interaction, command routing, and error display,
while delegating business logic to the appropriate services.

Test change: Version bump test
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from plato.sdk import Plato
# from plato.hub import Hub  # Not used
# from plato.sandbox import Sandbox  # Not used
# from plato.sandbox_sdk import PlatoSandboxSDK  # Deprecated, use PlatoSandboxClient
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


def _find_bundled_cli() -> Optional[str]:
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




async def run_interactive_sandbox_menu(sandbox):
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


async def handle_run_all(sandbox):
    # Deprecated; kept for compatibility but directs users to new commands
    console.print(
        "[yellow]⚠️ 'Run All' is deprecated. Use 'Run Services' then 'Run Worker'.[/yellow]"
    )


async def handle_display_sandbox_info(sandbox):
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


async def handle_sim_backup(sandbox):
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    console.print("[cyan]💾 Creating simulator backup...[/cyan]")

    try:
        await sandbox.client.backup_environment(sandbox.sandbox_info.public_id)
    except Exception as e:
        console.print(f"[red]❌ Error creating backup: {e}[/red]")


async def handle_sim_reset(sandbox):
    if not sandbox.sandbox_info:
        console.print("[red]❌ Sandbox not properly initialized[/red]")
        return

    console.print("[cyan]🔄 Resetting simulator environment...[/cyan]")

    try:
        await sandbox.client.reset_environment(sandbox.sandbox_info.public_id)
    except Exception as e:
        console.print(f"[red]❌ Error resetting simulator: {e}[/red]")


async def handle_run_services(sandbox):
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

            start_result = await sandbox._monitor_sse_stream_with_data(
                sandbox.client,
                submit.correlation_id,
                "Start Services",
                timeout=900,
            )
            if not start_result.success:
                progress.update(task, description="[red]Start-services failed[/red]")
                console.print(
                    f"[red]❌ Error starting services: {start_result.error or 'unknown error'}[/red]"
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
                health_result = await sandbox._monitor_sse_stream_with_data(
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


async def handle_run_worker(sandbox):
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
            start_result = await sandbox._monitor_sse_stream_with_data(
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
                breakpoint()
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
                result_h = await sandbox._monitor_sse_stream_with_data(
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


async def handle_create_snapshot(sandbox):
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
            result = await sandbox._monitor_sse_stream_with_data(
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
        console.print("\n[yellow]The bundled CLI binary was not found in this installation.[/yellow]")
        console.print("This indicates an installation issue with the plato-sdk package.")
        console.print("\n[yellow]💡 Try reinstalling the package:[/yellow]")
        console.print("   pip install --upgrade --force-reinstall plato-sdk")
        console.print("\n[dim]If the issue persists, please report it at:[/dim]")
        console.print("[dim]https://github.com/plato-app/plato-client/issues[/dim]")
        raise typer.Exit(1)

    # Get any additional arguments passed after 'hub'
    args = ctx.args if hasattr(ctx, 'args') else []

    try:
        # Launch the Go CLI, passing through all arguments
        # Use execvp to replace the current process so the TUI works properly
        os.execvp(plato_bin, [plato_bin] + args)
    except Exception as e:
        console.print(f"[red]❌ Failed to launch Plato Hub: {e}[/red]")
        raise typer.Exit(1)


def main():
    """Main entry point for the Plato CLI."""
    app()


# Backward compatibility
cli = main

if __name__ == "__main__":
    main()
