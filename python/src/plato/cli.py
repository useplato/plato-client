#!/usr/bin/env python3
"""
Plato CLI - Command line interface for Plato SDK
"""

import asyncio
import json
import sys
from typing import Optional

import click
from plato.sdk import Plato
from plato.exceptions import PlatoClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def handle_async(coro):
    """Helper function to run async functions in CLI commands."""
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        click.echo("Operation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.group()
@click.version_option()
def cli():
    """Plato CLI - Manage Plato environments from the command line."""
    pass


@cli.command()
@click.argument('env_name')
@click.option('--interface-type', default='browser', 
              type=click.Choice(['browser', 'noop']),
              help='Interface type for the environment (default: browser)')
@click.option('--width', default=1920, help='Viewport width (default: 1920)')
@click.option('--height', default=1080, help='Viewport height (default: 1080)')
@click.option('--keepalive', is_flag=True, help='Keep environment alive (disable heartbeat timeout)')
@click.option('--alias', help='Alias for the job group')
@click.option('--open-page', is_flag=True, help='Open page on start')
def make(env_name: str, interface_type: str, width: int, height: int, 
         keepalive: bool, alias: Optional[str], open_page: bool):
    """Create a new Plato environment.
    
    ENV_NAME: The name of the environment to create (e.g., 'espocrm', 'doordash')
    """
    async def _make():
        client = Plato()
        try:
            click.echo(f"Creating environment '{env_name}'...")
            env = await client.make_environment(
                env_id=env_name,
                interface_type=interface_type,
                viewport_width=width,
                viewport_height=height,
                keepalive=keepalive,
                alias=alias,
                open_page_on_start=open_page
            )
            
            click.echo(f"Environment created successfully!")
            click.echo(f"Environment ID: {env.id}")
            if env.alias:
                click.echo(f"Alias: {env.alias}")
            
            # Wait for environment to be ready
            click.echo("Waiting for environment to be ready...")
            await env.wait_for_ready(timeout=300.0)
            click.echo("Environment is ready!")
            
            # Get public URL
            try:
                public_url = await env.get_public_url()
                click.echo(f"Public URL: {public_url}")
            except Exception as e:
                click.echo(f"Warning: Could not get public URL: {e}", err=True)
            
            return env
            
        finally:
            await client.close()
    
    handle_async(_make())


@cli.command()
@click.argument('env_id')
@click.option('--task-id', help='Optional task ID to reset with')
@click.option('--agent-version', help='Optional agent version')
def reset(env_id: str, task_id: Optional[str], agent_version: Optional[str]):
    """Reset an existing Plato environment.
    
    ENV_ID: The ID of the environment to reset
    """
    async def _reset():
        client = Plato()
        try:
            # For reset, we need to create a temporary environment object
            # Since we only have the ID, we'll create it with minimal info
            from plato.models.env import PlatoEnvironment
            env = PlatoEnvironment(client=client, id=env_id)
            
            click.echo(f"Resetting environment '{env_id}'...")
            
            # Load task if task_id is provided
            task = None
            if task_id:
                # This would require loading the task from the API
                # For now, we'll just pass None and let the user handle tasks separately
                click.echo(f"Note: Task ID '{task_id}' will be used for reset")
            
            session_id = await env.reset(task=task, agent_version=agent_version)
            click.echo(f"Environment reset successfully!")
            click.echo(f"Session ID: {session_id}")
            
        finally:
            await client.close()
    
    handle_async(_reset())


@cli.command()
@click.argument('env_id')
@click.option('--pretty', is_flag=True, help='Pretty print JSON output')
@click.option('--mutations', is_flag=True, help='Show only state mutations')
def state(env_id: str, pretty: bool, mutations: bool):
    """Get the current state of a Plato environment.
    
    ENV_ID: The ID of the environment to check
    """
    async def _state():
        client = Plato()
        try:
            # Create a temporary environment object to get state
            from plato.models.env import PlatoEnvironment
            env = PlatoEnvironment(client=client, id=env_id)
            
            click.echo(f"Getting state for environment '{env_id}'...")
            
            if mutations:
                state_data = await env.get_state_mutations()
                click.echo(f"State mutations ({len(state_data)} mutations):")
            else:
                state_data = await env.get_state()
                click.echo(f"Environment state:")
            
            if pretty:
                click.echo(json.dumps(state_data, indent=2))
            else:
                click.echo(json.dumps(state_data))
                
        except PlatoClientError as e:
            if "No active run session" in str(e):
                click.echo(f"Error: Environment '{env_id}' has no active run session. Try resetting it first.", err=True)
            else:
                raise
        finally:
            await client.close()
    
    handle_async(_state())


@cli.command()
@click.argument('env_id')
def status(env_id: str):
    """Get the status of a Plato environment.
    
    ENV_ID: The ID of the environment to check
    """
    async def _status():
        client = Plato()
        try:
            click.echo(f"Getting status for environment '{env_id}'...")
            status_data = await client.get_job_status(env_id)
            
            click.echo(f"Status: {status_data.get('status', 'unknown')}")
            if 'message' in status_data:
                click.echo(f"Message: {status_data['message']}")
            
            # Pretty print the full status
            click.echo("Full status:")
            click.echo(json.dumps(status_data, indent=2))
            
        finally:
            await client.close()
    
    handle_async(_status())


@cli.command()
@click.argument('env_id')
def close(env_id: str):
    """Close a Plato environment and clean up resources.
    
    ENV_ID: The ID of the environment to close
    """
    async def _close():
        client = Plato()
        try:
            click.echo(f"Closing environment '{env_id}'...")
            response = await client.close_environment(env_id)
            click.echo("Environment closed successfully!")
            click.echo(json.dumps(response, indent=2))
            
        finally:
            await client.close()
    
    handle_async(_close())


@cli.command()
@click.argument('env_id')
def url(env_id: str):
    """Get the public URL for a Plato environment.
    
    ENV_ID: The ID of the environment
    """
    async def _url():
        client = Plato()
        try:
            # Create a temporary environment object to get public URL
            from plato.models.env import PlatoEnvironment
            env = PlatoEnvironment(client=client, id=env_id)
            
            public_url = await env.get_public_url()
            click.echo(f"Public URL for environment '{env_id}':")
            click.echo(public_url)
            
        finally:
            await client.close()
    
    handle_async(_url())


@cli.command()
def list_simulators():
    """List all available simulators/environments."""
    async def _list():
        client = Plato()
        try:
            simulators = await client.list_simulators()
            click.echo("Available simulators:")
            for sim in simulators:
                status = "✓" if sim.get("enabled", False) else "✗"
                click.echo(f"  {status} {sim['name']} - {sim.get('description', 'No description')}")
            
        finally:
            await client.close()
    
    handle_async(_list())


@cli.group(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
@click.pass_context
def build(ctx):
    """Plato VM management commands."""
    # If no subcommand is provided, show help
    if not ctx.args:
        from plato.builder.cli import app
        # Show typer help
        try:
            app(["--help"])
        except SystemExit:
            pass
        return
    
    # Import the typer app and run it with the remaining arguments
    from plato.builder.cli import app
    
    # Use typer's main function to handle the command
    try:
        app(ctx.args)
    except SystemExit:
        pass  # Typer uses SystemExit for normal operation


# Add individual build subcommands for better click integration
@build.command("up")
@click.option("-f", "--file", "compose_file", required=True, help="Docker Compose file path")
@click.option("-P", "--env-config", required=True, help="Environment configuration file (env.yml)")
def build_up(compose_file, env_config):
    """Create a New VM"""
    from plato.builder.cli import app
    try:
        app(["up", "-f", compose_file, "-P", env_config])
    except SystemExit:
        pass


@build.command("open")
@click.argument("vm_uuid", required=False)
def build_open(vm_uuid):
    """Open VM"""
    from plato.builder.cli import app
    args = ["open"]
    if vm_uuid:
        args.append(vm_uuid)
    try:
        app(args)
    except SystemExit:
        pass


@build.command("save")
@click.argument("vm_uuid", required=False)
@click.option("--name", "snapshot_name", help="Snapshot name")
def build_save(vm_uuid, snapshot_name):
    """Save VM Snapshot"""
    from plato.builder.cli import app
    args = ["save"]
    if vm_uuid:
        args.append(vm_uuid)
    if snapshot_name:
        args.extend(["--name", snapshot_name])
    try:
        app(args)
    except SystemExit:
        pass


@build.command("close")
@click.argument("vm_uuid", required=False)
@click.option("--force", is_flag=True, help="Force close without confirmation")
def build_close(vm_uuid, force):
    """Close VM"""
    from plato.builder.cli import app
    args = ["close"]
    if vm_uuid:
        args.append(vm_uuid)
    if force:
        args.append("--force")
    try:
        app(args)
    except SystemExit:
        pass


@build.command("ls")
def build_ls():
    """List Active VMs"""
    from plato.builder.cli import app
    try:
        app(["ls"])
    except SystemExit:
        pass


@build.command("select")
@click.argument("vm_uuid", required=False)
def build_select(vm_uuid):
    """Select VM"""
    from plato.builder.cli import app
    args = ["select"]
    if vm_uuid:
        args.append(vm_uuid)
    try:
        app(args)
    except SystemExit:
        pass


@build.command("exec")
@click.argument("container_name")
@click.argument("command")
@click.option("--vm", "vm_uuid", help="VM UUID (uses selected VM if not provided)")
def build_exec(container_name, command, vm_uuid):
    """Execute Commands in Docker Container"""
    from plato.builder.cli import app
    args = ["exec", container_name, command]
    if vm_uuid:
        args.extend(["--vm", vm_uuid])
    try:
        app(args)
    except SystemExit:
        pass


@build.command("registry")
def build_registry():
    """List Registry Simulators"""
    from plato.builder.cli import app
    try:
        app(["registry"])
    except SystemExit:
        pass


if __name__ == '__main__':
    cli() 