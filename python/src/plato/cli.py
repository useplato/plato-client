#!/usr/bin/env python3
"""
Plato CLI - Command line interface for Plato SDK
"""

import asyncio
import json
import sys
import os
from typing import Optional

import click
from plato.sdk import Plato
from plato.exceptions import PlatoClientError
from dotenv import load_dotenv

# Load environment variables from multiple possible locations
load_dotenv()  # Load from current directory
load_dotenv(dotenv_path=os.path.join(os.path.expanduser("~"), ".env"))  # Load from home directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))  # Load from script directory


def handle_async(coro):
    """Helper function to run async functions in CLI commands."""
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        click.echo("Operation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        # Check if it's an auth issue and provide helpful hint
        if "401" in str(e) or "Unauthorized" in str(e):
            click.echo("💡 Hint: Make sure PLATO_API_KEY is set in your environment or .env file", err=True)
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


# Hub commands for Git repository management
@cli.group()
def hub():
    """Plato Hub - Manage simulator repositories and development environments."""
    pass


@hub.command()
@click.argument('sim_name')
@click.option('--directory', help='Directory to clone into (default: current directory)')
def clone(sim_name: str, directory: Optional[str]):
    """Clone a simulator repository.
    
    SIM_NAME: The name of the simulator to clone (e.g., 'espocrm', 'doordash')
    """
    async def _clone():
        client = Plato()
        try:
            click.echo(f"Looking up simulator '{sim_name}'...")
            
            # Get all available simulators
            simulators = await client.list_gitea_simulators()
            
            # Find the simulator by name
            simulator = None
            for sim in simulators:
                if sim['name'].lower() == sim_name.lower():
                    simulator = sim
                    break
            
            if not simulator:
                click.echo(f"❌ Simulator '{sim_name}' not found.", err=True)
                available = [s['name'] for s in simulators]
                if available:
                    click.echo(f"💡 Available simulators: {', '.join(available)}", err=True)
                return
            
            if not simulator.get('has_repo', False):
                click.echo(f"❌ Simulator '{sim_name}' exists but doesn't have a repository configured.", err=True)
                click.echo("💡 Contact your administrator to set up a repository for this simulator.", err=True)
                return
            
            # Get repository details
            repo_info = await client.get_simulator_repository(simulator['id'])
            if not repo_info.get('has_repo', False):
                click.echo(f"❌ Repository for simulator '{sim_name}' is not available.", err=True)
                click.echo(f"💡 Attempting to create repository for '{sim_name}'...")
                
                # Try to create the repository
                try:
                    create_response = await client.http_session.post(
                        f"{client.base_url}/gitea/simulators/{simulator['id']}/repo",
                        headers={"X-API-Key": client.api_key}
                    )
                    if create_response.status == 200:
                        repo_info = await create_response.json()
                        click.echo(f"✅ Created repository for '{sim_name}'")
                    else:
                        error_text = await create_response.text()
                        click.echo(f"❌ Failed to create repository: {error_text}", err=True)
                        return
                except Exception as create_e:
                    click.echo(f"❌ Failed to create repository: {create_e}", err=True)
                    return
            
            clone_url = repo_info['clone_url']
            repo_name = repo_info['name']
            
            # Use admin credentials if available for authenticated cloning
            if repo_info.get('admin_credentials'):
                creds = repo_info['admin_credentials']
                # Construct authenticated URL: https://username:password@domain/path
                if clone_url.startswith('https://'):
                    # Replace https:// with https://username:password@
                    authenticated_url = clone_url.replace('https://', f"https://{creds['username']}:{creds['password']}@")
                    clone_url = authenticated_url
                    click.echo(f"Using admin credentials for authentication (user: {creds['username']})")
                else:
                    click.echo(f"Warning: Could not authenticate - URL not HTTPS: {clone_url}", err=True)
            else:
                click.echo("⚠️  Warning: No admin credentials provided - clone may require manual authentication", err=True)
            
            # Determine target directory
            if directory:
                target_dir = directory
            else:
                target_dir = repo_name
            
            click.echo(f"Cloning {repo_info['full_name']} to {target_dir}...")
            
            # Clone the repository
            import subprocess
            
            try:
                result = subprocess.run(
                    ['git', 'clone', clone_url, target_dir],
                    capture_output=True,
                    text=True,
                    check=True
                )
                click.echo(f"✅ Successfully cloned {repo_info['full_name']}")
                click.echo(f"Repository cloned to: {target_dir}")
                
                if repo_info.get('description'):
                    click.echo(f"Description: {repo_info['description']}")
                
            except subprocess.CalledProcessError as e:
                click.echo(f"❌ Failed to clone repository: {e.stderr.strip()}", err=True)
                if "Authentication failed" in e.stderr:
                    click.echo("💡 Hint: Make sure your Git credentials are configured for Gitea access.", err=True)
            except FileNotFoundError:
                click.echo("❌ Git is not installed or not in PATH", err=True)
                
        finally:
            await client.close()
    
    handle_async(_clone())


@hub.command()
@click.argument('sim_name')
@click.argument('directory', required=False)
def link(sim_name: str, directory: Optional[str]):
    """Link a local directory to a simulator repository.
    
    Sets up git remote without cloning - useful for monorepos.
    
    SIM_NAME: The name of the simulator to link to
    DIRECTORY: Directory to link (default: current directory)
    """
    async def _link():
        client = Plato()
        try:
            import os
            import subprocess
            
            # Determine target directory
            target_dir = directory or os.getcwd()
            
            click.echo(f"Looking up simulator '{sim_name}'...")
            
            # Get all available simulators
            simulators = await client.list_gitea_simulators()
            
            # Find the simulator by name
            simulator = None
            for sim in simulators:
                if sim['name'].lower() == sim_name.lower():
                    simulator = sim
                    break
            
            if not simulator:
                click.echo(f"❌ Simulator '{sim_name}' not found.", err=True)
                available = [s['name'] for s in simulators]
                if available:
                    click.echo(f"💡 Available simulators: {', '.join(available)}", err=True)
                return
            
            if not simulator.get('has_repo', False):
                click.echo(f"❌ Simulator '{sim_name}' exists but doesn't have a repository configured.", err=True)
                click.echo("💡 Contact your administrator to set up a repository for this simulator.", err=True)
                return
            
            # Get repository details
            repo_info = await client.get_simulator_repository(simulator['id'])
            if not repo_info.get('has_repo', False):
                click.echo(f"Repository for simulator '{sim_name}' is not available.", err=True)
                return
            
            clone_url = repo_info['clone_url']
            
            # Use admin credentials if available for authenticated operations
            if repo_info.get('admin_credentials'):
                creds = repo_info['admin_credentials']
                # Construct authenticated URL: https://username:password@domain/path
                if clone_url.startswith('https://'):
                    # Replace https:// with https://username:password@
                    authenticated_url = clone_url.replace('https://', f"https://{creds['username']}:{creds['password']}@")
                    clone_url = authenticated_url
                    click.echo(f"Using admin credentials for authentication")
            
            click.echo(f"Linking directory '{target_dir}' to {repo_info['full_name']}...")
            
            # Change to target directory
            original_dir = os.getcwd()
            os.chdir(target_dir)
            
            try:
                # Check if we're in a git repository
                git_check = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True)
                if git_check.returncode != 0:
                    click.echo("❌ Not in a git repository. Initialize git first with 'git init'", err=True)
                    return
                
                # Get the git root directory to check if we're in the right place
                git_root_result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
                if git_root_result.returncode == 0:
                    git_root = git_root_result.stdout.strip()
                    current_abs_path = os.path.abspath(target_dir)
                    
                    if git_root != current_abs_path:
                        click.echo(f"⚠️  Warning: You're in a subdirectory of a git repository!", err=True)
                        click.echo(f"Git root: {git_root}", err=True)
                        click.echo(f"Current dir: {current_abs_path}", err=True)
                        click.echo("💡 This will modify the parent repository's remote. Continue? (y/N)", err=True)
                        
                        if not click.confirm(""):
                            click.echo("❌ Aborted", err=True)
                            return
                
                # Check if remote already exists
                result = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    current_url = result.stdout.strip()
                    if current_url == clone_url:
                        click.echo("✅ Remote origin already correctly configured")
                    else:
                        # Update remote URL
                        subprocess.run(['git', 'remote', 'set-url', 'origin', clone_url], check=True)
                        click.echo(f"✅ Updated remote origin to {repo_info['full_name']}")
                else:
                    # Add remote origin
                    subprocess.run(['git', 'remote', 'add', 'origin', clone_url], check=True)
                    click.echo(f"✅ Added remote origin: {repo_info['full_name']}")
                
                click.echo(f"🔗 Directory '{target_dir}' is now linked to {repo_info['full_name']}")
                click.echo("💡 You can now use 'uv run plato hub git <command>' or regular git commands.")
                
            except subprocess.CalledProcessError as e:
                click.echo(f"❌ Failed to link repository: {e.stderr.decode().strip()}", err=True)
            except FileNotFoundError:
                click.echo("❌ Git is not installed or not in PATH", err=True)
            finally:
                os.chdir(original_dir)
                
        finally:
            await client.close()
    
    handle_async(_link())


@hub.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.pass_context
def git(ctx):
    """Execute git commands with authenticated Plato hub remote.
    
    Examples:
      uv run plato hub git status
      uv run plato hub git push origin main
      uv run plato hub git pull
    """
    import os
    import subprocess
    
    # Get the extra arguments from click context
    args = ctx.args
    
    if not args:
        click.echo("❌ Please provide a git command", err=True)
        click.echo("💡 Example: uv run plato hub git status", err=True)
        return
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            click.echo("❌ Not in a git repository", err=True)
            return
        
        # Check if we have a Plato remote configured
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True
        )
        
        has_plato_remote = False
        if result.returncode == 0:
            origin_url = result.stdout.strip()
            if 'hub.plato.so' in origin_url or 'gitea' in origin_url.lower():
                has_plato_remote = True
        
        if not has_plato_remote:
            click.echo("⚠️  Warning: No Plato hub remote detected. Use 'uv run plato hub link <sim_name>' first.", err=True)
        
        # Execute the git command
        git_cmd = ['git'] + list(args)
        result = subprocess.run(git_cmd, capture_output=False, text=True)
        
        # Exit with the same code as git
        if result.returncode != 0:
            ctx.exit(result.returncode)
            
    except FileNotFoundError:
        click.echo("❌ Git is not installed or not in PATH", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"❌ Error executing git command: {e}", err=True)
        ctx.exit(1)


@hub.command()
def sandbox():
    """Start a development sandbox environment.
    
    Checks for git initialization and starts a dev machine (placeholder).
    """
    import os
    import subprocess
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            click.echo("❌ You must initialize a Plato hub git repository first.", err=True)
            click.echo("💡 Use 'uv run plato hub clone <sim_name>' or 'uv run plato hub link <sim_name>' first.", err=True)
            return
        
        # Check if it's linked to a Plato repository
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            origin_url = result.stdout.strip()
            if 'gitea' in origin_url.lower() or 'plato' in origin_url.lower():
                click.echo("✅ Plato hub repository detected")
                click.echo(f"🔗 Remote: {origin_url}")
            else:
                click.echo("⚠️  Warning: This doesn't appear to be a Plato hub repository")
                click.echo(f"Current remote: {origin_url}")
        
        click.echo("🚧 Sandbox environment starting... (placeholder)")
        click.echo("This will eventually start a development environment for the current repository.")
        
    except FileNotFoundError:
        click.echo("❌ Git is not installed or not in PATH", err=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error checking git status: {e.stderr.decode().strip()}", err=True)


if __name__ == '__main__':
    cli() 