#!/usr/bin/env python3
"""
Plato Builder CLI - VM management commands using typer
"""

import asyncio
import os
import time
import uuid
from typing import List, Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .models import EnvironmentConfig, VMJob

# Initialize typer app and console
app = typer.Typer(name="plato-builder", help="Plato VM management CLI")
console = Console()

# Global state for active VMs and selected VM
ACTIVE_VMS: List[VMJob] = []
SELECTED_VM: Optional[VMJob] = None


def handle_async(coro):
    """Helper function to run async functions in CLI commands."""
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        console.print("Operation cancelled by user.", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)


def load_environment_config(config_path: str) -> EnvironmentConfig:
    """Load and validate environment configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return EnvironmentConfig(**config_data)
    except FileNotFoundError:
        console.print(f"[red]Error: Configuration file '{config_path}' not found[/red]")
        raise typer.Exit(1)
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML configuration: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


def validate_docker_compose(compose_path: str) -> bool:
    """Validate that docker-compose file exists"""
    if not os.path.exists(compose_path):
        console.print(f"[red]Error: Docker Compose file '{compose_path}' not found[/red]")
        return False
    return True


def generate_job_uuid() -> str:
    """Generate a unique job UUID"""
    return str(uuid.uuid4())[:8]


async def create_vm_with_sdk(compose_file: str, env_config: str, config: EnvironmentConfig) -> VMJob:
    """Create VM using the Plato SDK"""
    from plato.sdk import Plato
    
    client = Plato()
    try:
        # Step 1: Create VM with configuration parameters
        console.print("[dim]Step 1/2: Creating VM and waiting for it to start...[/dim]")
        vm_data = await client.create_vm(
            service_name=config.plato.sim_name,
            alias=config.plato.sim_name,
            vcpu_count=config.plato.vcpus,
            mem_size_mib=config.plato.memory,
            overlay_size_mb=config.plato.storage,
            port=config.plato.access_port,
            messaging_port=config.plato.messaging_port
        )
        
        vm_uuid = vm_data["uuid"]
        
        # Step 2: Configure VM with Docker Compose and environment files
        console.print("[dim]Step 2/2: Configuring VM with Docker Compose and environment files...[/dim]")
        await client.configure_vm(
            vm_uuid=vm_uuid,
            compose_file_path=compose_file,
            env_config_path=env_config
        )
        
        job = VMJob(
            uuid=vm_data["uuid"],
            name=vm_data["name"],
            status=vm_data["status"],
            time_started=vm_data["time_started"],
            url=vm_data["url"]
        )
        
        # Add to active VMs
        global ACTIVE_VMS
        ACTIVE_VMS.append(job)
        
        return job
        
    finally:
        await client.close()


@app.command("up")
def up(
    compose_file: str = typer.Option(..., "-f", "--file", help="Docker Compose file path"),
    env_config: str = typer.Option(..., "-P", "--env-config", help="Environment configuration file (env.yml)")
):
    """
    Create a New VM
    
    Starts a new VM with a Docker Compose and environment config.
    """
    global SELECTED_VM
    console.print("[bold blue]Starting new Plato VM...[/bold blue]")
    
    # Validate inputs
    if not validate_docker_compose(compose_file):
        raise typer.Exit(1)
    
    # Load environment configuration
    config = load_environment_config(env_config)
    
    # Display configuration summary
    console.print(f"[green]✓[/green] Docker Compose: {compose_file}")
    console.print(f"[green]✓[/green] Environment Config: {env_config}")
    console.print(f"[green]✓[/green] Simulation Name: {config.plato.sim_name}")
    console.print(f"[green]✓[/green] vCPUs: {config.plato.vcpus}")
    console.print(f"[green]✓[/green] Memory: {config.plato.memory}MB")
    console.print(f"[green]✓[/green] Storage: {config.plato.storage}MB")
    
    if config.db:
        console.print(f"[green]✓[/green] Database: {config.db.db_type} v{config.db.db_version}")
    
    # Create VM with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating VM...", total=None)
        
        # Create job using SDK
        async def _create_vm():
            progress.update(task, description="Creating VM...")
            return await create_vm_with_sdk(compose_file, env_config, config)
        
        job = handle_async(_create_vm())
        
        progress.update(task, description="VM created and running!")
        time.sleep(1)  # Brief pause to show completion
    
    # Display results
    status_style = "green" if job.status == "running" else "yellow" if job.status == "starting" else "red"
    status_message = "VM started successfully!" if job.status == "running" else f"VM status: {job.status}"
    
    console.print(f"\n[bold {status_style}]{status_message}[/bold {status_style}]")
    console.print(f"Job UUID: [bold]{job.uuid}[/bold]")
    console.print(f"Name: [bold]{job.name}[/bold]")
    console.print(f"Time Started: [bold]{job.time_started}[/bold]")
    console.print(f"Status: [bold {status_style}]{job.status}[/bold {status_style}]")
    console.print(f"URL: [bold blue]{job.url}[/bold blue]")
    
    # Set as selected VM
    global SELECTED_VM
    SELECTED_VM = job


@app.command("open")
def open_vm(
    vm_uuid: Optional[str] = typer.Argument(None, help="VM UUID (uses selected VM if not provided)")
):
    """
    Open VM
    
    Returns the public URL for the VM.
    """
    target_vm = None
    
    if vm_uuid:
        # Find VM by UUID
        target_vm = next((vm for vm in ACTIVE_VMS if vm.uuid == vm_uuid), None)
        if not target_vm:
            console.print(f"[red]Error: VM with UUID '{vm_uuid}' not found[/red]")
            raise typer.Exit(1)
    else:
        # Use selected VM
        if not SELECTED_VM:
            console.print("[red]Error: No VM selected. Use 'plato-builder select' first or provide a VM UUID[/red]")
            raise typer.Exit(1)
        target_vm = SELECTED_VM
    
    # Get URL from SDK (in case it's updated)
    async def _get_vm_url():
        from plato.sdk import Plato
        client = Plato()
        try:
            return await client.get_vm_url(target_vm.uuid)
        finally:
            await client.close()
    
    url = handle_async(_get_vm_url())
    
    console.print("[bold green]VM URL:[/bold green]")
    console.print(f"{url}")


@app.command("save")
def save_vm(
    vm_uuid: Optional[str] = typer.Argument(None, help="VM UUID (uses selected VM if not provided)"),
    snapshot_name: Optional[str] = typer.Option(None, "--name", help="Snapshot name")
):
    """
    Save VM Snapshot
    
    Saves a snapshot to the VM archive for later retrieval.
    """
    target_vm = None
    
    if vm_uuid:
        target_vm = next((vm for vm in ACTIVE_VMS if vm.uuid == vm_uuid), None)
        if not target_vm:
            console.print(f"[red]Error: VM with UUID '{vm_uuid}' not found[/red]")
            raise typer.Exit(1)
    else:
        if not SELECTED_VM:
            console.print("[red]Error: No VM selected. Use 'plato-builder select' first or provide a VM UUID[/red]")
            raise typer.Exit(1)
        target_vm = SELECTED_VM
    
    # Generate snapshot name if not provided
    if not snapshot_name:
        snapshot_name = f"{target_vm.name}-snapshot-{int(time.time())}"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating snapshot...", total=None)
        
        # Save snapshot using SDK
        async def _save_snapshot():
            from plato.sdk import Plato
            client = Plato()
            try:
                return await client.save_vm_snapshot(
                    target_vm.uuid, 
                    snapshot_name, 
                    service="vm-service",  # Default service name
                    version="latest",
                    timeout=1800
                )
            finally:
                await client.close()
        
        snapshot_data = handle_async(_save_snapshot())
    
    console.print("[bold green]Snapshot saved successfully![/bold green]")
    console.print(f"VM: [bold]{target_vm.name}[/bold] ({target_vm.uuid})")
    console.print(f"Snapshot: [bold]{snapshot_data['snapshot_name']}[/bold]")
    console.print(f"Snapshot ID: [bold]{snapshot_data['snapshot_id']}[/bold]")


@app.command("close")
def close_vm(
    vm_uuid: Optional[str] = typer.Argument(None, help="VM UUID (uses selected VM if not provided)"),
    force: bool = typer.Option(False, "--force", help="Force close without confirmation")
):
    """
    Close VM
    
    Terminates the VM and cleans up resources.
    """
    global ACTIVE_VMS, SELECTED_VM
    target_vm = None
    
    if vm_uuid:
        target_vm = next((vm for vm in ACTIVE_VMS if vm.uuid == vm_uuid), None)
        if not target_vm:
            console.print(f"[red]Error: VM with UUID '{vm_uuid}' not found[/red]")
            raise typer.Exit(1)
    else:
        if not SELECTED_VM:
            console.print("[red]Error: No VM selected. Use 'plato-builder select' first or provide a VM UUID[/red]")
            raise typer.Exit(1)
        target_vm = SELECTED_VM
    
    # Confirmation
    if not force:
        confirm = typer.confirm(f"Are you sure you want to close VM '{target_vm.name}' ({target_vm.uuid})?")
        if not confirm:
            console.print("Operation cancelled.")
            return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Stopping VM...", total=None)
        
        # Close VM using SDK
        async def _close_vm():
            from plato.sdk import Plato
            client = Plato()
            try:
                return await client.close_vm(target_vm.uuid)
            finally:
                await client.close()
        
        close_data = handle_async(_close_vm())
    
    # Remove from active VMs
    ACTIVE_VMS = [vm for vm in ACTIVE_VMS if vm.uuid != target_vm.uuid]
    
    # Clear selection if this was the selected VM
    if SELECTED_VM and SELECTED_VM.uuid == target_vm.uuid:
        SELECTED_VM = None
    
    console.print(f"[bold green]VM '{target_vm.name}' closed successfully![/bold green]")
    console.print(f"Status: [bold]{close_data['status']}[/bold]")


@app.command("ls")
def list_vms():
    """
    List Active VMs
    
    Shows all currently running VMs.
    """
    # Get VMs from SDK
    async def _list_vms():
        from plato.sdk import Plato
        client = Plato()
        try:
            return await client.list_active_vms()
        finally:
            await client.close()
    
    sdk_vms = handle_async(_list_vms())
    
    # Merge with local active VMs (for this session)
    # In a real implementation, you might want to sync these properly
    all_vms = ACTIVE_VMS.copy()
    
    # Add SDK VMs that aren't already in our local list
    local_uuids = {vm.uuid for vm in ACTIVE_VMS}
    for sdk_vm in sdk_vms:
        if sdk_vm['uuid'] not in local_uuids:
            vm_job = VMJob(
                uuid=sdk_vm['uuid'],
                name=sdk_vm['name'],
                status=sdk_vm['status'],
                time_started=sdk_vm['time_started'],
                url=sdk_vm.get('url', '')
            )
            all_vms.append(vm_job)
    
    if not all_vms:
        console.print("[yellow]No active VMs found.[/yellow]")
        return
    
    table = Table(title="Active VMs")
    table.add_column("Selected", style="green")
    table.add_column("UUID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="yellow")
    table.add_column("Started", style="blue")
    table.add_column("URL", style="green")
    
    for vm in all_vms:
        selected_mark = "✓" if SELECTED_VM and SELECTED_VM.uuid == vm.uuid else ""
        table.add_row(
            selected_mark,
            vm.uuid,
            vm.name,
            vm.status,
            vm.time_started,
            vm.url or ""
        )
    
    console.print(table)


@app.command("select")
def select_vm(
    vm_uuid: Optional[str] = typer.Argument(None, help="VM UUID to select")
):
    """
    Select VM
    
    Allows performing operations like save, close, etc. on the selected VM.
    """
    global ACTIVE_VMS, SELECTED_VM
    
    if not vm_uuid:
        # Interactive selection
        if not ACTIVE_VMS:
            console.print("[yellow]No active VMs to select from.[/yellow]")
            return
        
        console.print("[bold]Available VMs:[/bold]")
        for i, vm in enumerate(ACTIVE_VMS, 1):
            console.print(f"{i}. {vm.name} ({vm.uuid}) - {vm.status}")
        
        choice = typer.prompt("Select VM number", type=int)
        if 1 <= choice <= len(ACTIVE_VMS):
            vm_uuid = ACTIVE_VMS[choice - 1].uuid
        else:
            console.print("[red]Invalid selection.[/red]")
            return
    
    # Find and select VM
    target_vm = next((vm for vm in ACTIVE_VMS if vm.uuid == vm_uuid), None)
    if not target_vm:
        console.print(f"[red]Error: VM with UUID '{vm_uuid}' not found[/red]")
        raise typer.Exit(1)
    
    SELECTED_VM = target_vm
    console.print(f"[bold green]Selected VM:[/bold green] {target_vm.name} ({target_vm.uuid})")


@app.command("exec")
def exec_command(
    container_name: str = typer.Argument(..., help="Container name"),
    command: str = typer.Argument(..., help="Command to execute"),
    vm_uuid: Optional[str] = typer.Option(None, "--vm", help="VM UUID (uses selected VM if not provided)")
):
    """
    Execute Commands in Docker Container
    
    Runs a command inside a specific container in the VM.
    """
    target_vm = None
    
    if vm_uuid:
        target_vm = next((vm for vm in ACTIVE_VMS if vm.uuid == vm_uuid), None)
        if not target_vm:
            console.print(f"[red]Error: VM with UUID '{vm_uuid}' not found[/red]")
            raise typer.Exit(1)
    else:
        if not SELECTED_VM:
            console.print("[red]Error: No VM selected. Use 'plato-builder select' first or provide a VM UUID[/red]")
            raise typer.Exit(1)
        target_vm = SELECTED_VM
    
    console.print(f"[bold]Executing in VM:[/bold] {target_vm.name} ({target_vm.uuid})")
    console.print(f"[bold]Container:[/bold] {container_name}")
    console.print(f"[bold]Command:[/bold] {command}")
    console.print()
    
    # Execute command using SDK
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing command...", total=None)
        
        async def _execute_command():
            from plato.sdk import Plato
            client = Plato()
            try:
                return await client.execute_vm_command(target_vm.uuid, container_name, command)
            finally:
                await client.close()
        
        exec_result = handle_async(_execute_command())
    
    # Display execution results
    console.print("[bold green]Command executed successfully![/bold green]")
    console.print(f"Exit Code: [bold]{exec_result['exit_code']}[/bold]")
    console.print(f"Execution Time: [bold]{exec_result['execution_time_ms']}ms[/bold]")
    
    if exec_result['stdout']:
        console.print("\n[bold]Output:[/bold]")
        console.print(exec_result['stdout'])
    
    if exec_result['stderr']:
        console.print("\n[bold red]Error Output:[/bold red]")
        console.print(exec_result['stderr'])


@app.command("registry")
def registry():
    """
    List Registry Simulators
    
    Shows all simulators available in the registry for your organization.
    """
    # Get simulators from SDK
    async def _list_registry():
        from plato.sdk import Plato
        client = Plato()
        try:
            return await client.list_registry_simulators()
        finally:
            await client.close()
    
    simulators = handle_async(_list_registry())
    
    if not simulators:
        console.print("[yellow]No simulators found in registry.[/yellow]")
        return
    
    # Create table to display registry
    table = Table(title="Simulator Registry")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Description", style="white", max_width=40)
    table.add_column("Type", style="blue")
    table.add_column("Enabled", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Port", style="dim")
    
    for sim in simulators:
        # Format enabled status
        enabled_status = "✅ Yes" if sim.get("enabled", False) else "❌ No"
        
        # Format description - truncate if too long
        description = sim.get("description") or "No description"
        if len(description) > 37:
            description = description[:34] + "..."
        
        # Format port
        port_info = str(sim.get("internal_app_port", "N/A"))
        
        table.add_row(
            str(sim.get("id", "")),
            sim.get("name", "Unknown"),
            description,
            sim.get("sim_type", "unknown"),
            enabled_status,
            sim.get("version_tag", "latest"),
            port_info
        )
    
    console.print(table)
    console.print(f"\n[dim]Total simulators: {len(simulators)}[/dim]")


if __name__ == "__main__":
    app()
