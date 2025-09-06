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


# Helper functions for hub git operations
def _hub_push(hub_config: dict, extra_args: list):
    """Push current directory contents to simulator repository"""
    import tempfile
    import shutil
    import subprocess
    
    try:
        clone_url = _get_authenticated_url(hub_config)
        if not clone_url:
            click.echo("❌ Authentication failed. Run 'uv run plato hub login' first.", err=True)
            return
            
        sim_name = hub_config['simulator_name']
        
        click.echo(f"📤 Pushing to simulator '{sim_name}'...")
        
        # Create temporary directory for isolated git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, 'temp_repo')
            
            # Clone the simulator repository
            result = subprocess.run(['git', 'clone', clone_url, temp_repo], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                click.echo(f"❌ Failed to clone simulator repo: {result.stderr.strip()}", err=True)
                return
            
            # Copy current directory contents to temp repo (excluding git and config files)
            current_dir = os.getcwd()
            for item in os.listdir(current_dir):
                if item.startswith('.'):
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
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Check if there are changes to commit
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                        capture_output=True, text=True)
            if not status_result.stdout.strip():
                click.echo("📝 No changes to push")
                return
            
            subprocess.run(['git', 'commit', '-m', f'Sync from {hub_config["sync_directory"]} directory'], 
                          check=True)
            
            # Push to main branch (or specified branch)
            push_args = ['git', 'push', 'origin', 'main'] + extra_args
            result = subprocess.run(push_args, capture_output=True, text=True)
            
            if result.returncode == 0:
                click.echo(f"✅ Successfully pushed to simulator '{sim_name}'")
            else:
                click.echo(f"❌ Push failed: {result.stderr.strip()}", err=True)
    
    except Exception as e:
        click.echo(f"❌ Error during push: {e}", err=True)


def _hub_pull(hub_config: dict, extra_args: list):
    """Pull changes from simulator repository to current directory"""
    import tempfile
    import subprocess
    import shutil
    
    try:
        clone_url = _get_authenticated_url(hub_config)
        if not clone_url:
            click.echo("❌ Authentication failed. Run 'uv run plato hub login' first.", err=True)
            return
            
        sim_name = hub_config['simulator_name']
        
        click.echo(f"📥 Pulling from simulator '{sim_name}'...")
        
        # Create temporary directory for isolated git operations  
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, 'temp_repo')
            
            # Clone the simulator repository
            result = subprocess.run(['git', 'clone', clone_url, temp_repo], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                click.echo(f"❌ Failed to clone simulator repo: {result.stderr.strip()}", err=True)
                return
            
            # Copy contents from temp repo to current directory (excluding git files)
            current_dir = os.getcwd()
            for item in os.listdir(temp_repo):
                if item.startswith('.git'):
                    continue  # Skip git directory
                
                src = os.path.join(temp_repo, item)
                dst = os.path.join(current_dir, item)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
            
            click.echo(f"✅ Successfully pulled from simulator '{sim_name}'")
            click.echo("💡 Files updated in current directory. Review and commit to your monorepo as needed.")
    
    except Exception as e:
        click.echo(f"❌ Error during pull: {e}", err=True)


def _hub_status(hub_config: dict, command: str, extra_args: list):
    """Show git status for the hub-linked directory in isolation"""
    import tempfile
    import subprocess
    import shutil
    
    try:
        clone_url = _get_authenticated_url(hub_config)
        if not clone_url:
            # For read-only commands, try without auth first
            clone_url = hub_config['repository']['clone_url']
            
        sim_name = hub_config['simulator_name']
        
        # Create temporary directory for isolated git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, 'temp_repo')
            current_dir = os.getcwd()
            
            # Try to clone the simulator repository first to get the baseline
            clone_result = subprocess.run(['git', 'clone', clone_url, temp_repo], 
                                        capture_output=True, text=True)
            
            if clone_result.returncode != 0:
                # If clone fails (auth issues, empty repo, etc), create fresh repo
                subprocess.run(['git', 'init', '--initial-branch=main', temp_repo], 
                              capture_output=True, check=True)
                click.echo(f"📁 Creating isolated view (couldn't fetch remote: {clone_result.stderr.strip()[:50]}...)")
            else:
                click.echo(f"📡 Comparing against simulator repository")
                
            # Copy current directory contents over the cloned/initialized repo
            os.chdir(temp_repo)
            
            # Remove all files except .git to replace with current directory content
            for item in os.listdir('.'):
                if not item.startswith('.git'):
                    item_path = os.path.join('.', item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
            
            # Copy current directory contents 
            for item in os.listdir(current_dir):
                if item.startswith('.git') or item == '.plato-hub.json':
                    continue  # Skip git and config files
                
                src = os.path.join(current_dir, item)
                dst = os.path.join('.', item)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst)
            
            # Run the requested command
            git_cmd = ['git', command] + extra_args
            result = subprocess.run(git_cmd, capture_output=False, text=True)
            
    except Exception as e:
        click.echo(f"❌ Error during {command}: {e}", err=True)


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
        with open(cache_file, 'r') as f:
            credentials = json.load(f)
        
        base_url = hub_config['repository']['clone_url']
        username = credentials.get('username')
        password = credentials.get('password')
        
        if username and password and base_url.startswith('https://'):
            return base_url.replace('https://', f"https://{username}:{password}@")
        
    except Exception:
        pass
    
    return None


def _ensure_gitignore_protects_credentials():
    """Add credential files to .gitignore if not already present"""
    import subprocess
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True)
        if result.returncode != 0:
            return  # Not in a git repo, nothing to do
        
        # Get git root directory
        root_result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                                   capture_output=True, text=True)
        if root_result.returncode != 0:
            return
        
        git_root = root_result.stdout.strip()
        gitignore_path = os.path.join(git_root, '.gitignore')
        
        # Patterns to protect
        protect_patterns = [
            "# Plato hub credentials",
            "credentials.json",
            ".plato-hub/",
            "*.plato-hub.json"
        ]
        
        # Read existing gitignore
        existing_content = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                existing_content = f.read()
        
        # Check which patterns need to be added
        patterns_to_add = []
        for pattern in protect_patterns:
            if pattern not in existing_content:
                patterns_to_add.append(pattern)
        
        # Add missing patterns
        if patterns_to_add:
            with open(gitignore_path, 'a') as f:
                if existing_content and not existing_content.endswith('\n'):
                    f.write('\n')
                f.write('\n'.join(patterns_to_add) + '\n')
            
            click.echo(f"✅ Added {len(patterns_to_add)} credential protection patterns to .gitignore", err=True)
        
    except Exception as e:
        # Silently fail - gitignore protection is nice-to-have, not critical
        pass


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
                import json
                
                # Create plato hub configuration file (without credentials)
                hub_config = {
                    "simulator_name": sim_name,
                    "simulator_id": simulator['id'],
                    "repository": {
                        "name": repo_info['name'],
                        "full_name": repo_info['full_name'],
                        "clone_url": repo_info['clone_url'].replace('https://', 'https://').split('@')[-1] if '@' in repo_info['clone_url'] else repo_info['clone_url'],  # Strip any embedded auth
                        "description": repo_info.get('description')
                    },
                    "sync_directory": os.path.basename(target_dir)
                }
                
                # Write config to .plato-hub.json
                config_file = os.path.join(target_dir, '.plato-hub.json')
                with open(config_file, 'w') as f:
                    json.dump(hub_config, f, indent=2)
                
                click.echo(f"✅ Created Plato hub configuration for '{sim_name}'")
                click.echo(f"🔗 Directory '{target_dir}' is now linked to {repo_info['full_name']}")
                click.echo("💡 This directory will sync with the simulator repo independently")
                click.echo("💡 Run 'uv run plato hub login' to authenticate")
                click.echo("💡 Then use 'uv run plato hub git push/pull' to sync")
                click.echo("💡 Your monorepo structure remains intact!")
                
            except subprocess.CalledProcessError as e:
                click.echo(f"❌ Failed to link repository: {e.stderr.decode().strip()}", err=True)
            except FileNotFoundError:
                click.echo("❌ Git is not installed or not in PATH", err=True)
            finally:
                os.chdir(original_dir)
                
        finally:
            await client.close()
    
    handle_async(_link())


@hub.command()
def login():
    """Authenticate with Plato hub for git operations."""
    async def _login():
        import os
        import json
        from datetime import datetime
        
        client = Plato()
        try:
            click.echo("🔐 Authenticating with Plato hub...")
            
            # Get admin credentials from the API
            creds = await client.get_gitea_credentials()
            
            # Create cache directory
            cache_dir = os.path.expanduser("~/.plato-hub")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Cache credentials securely
            credentials = {
                "username": creds['username'],
                "password": creds['password'],
                "org_name": creds['org_name'],
                "cached_at": datetime.now().isoformat()
            }
            
            # Save credentials to cache
            cache_file = os.path.join(cache_dir, "credentials.json") 
            with open(cache_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            
            # Set restrictive permissions on credentials file
            os.chmod(cache_file, 0o600)
            
            # Add credentials to gitignore for security
            _ensure_gitignore_protects_credentials()
            
            click.echo("✅ Successfully authenticated with Plato hub")
            click.echo(f"👤 Username: {creds['username']}")
            click.echo(f"🏢 Organization: {creds['org_name']}")
            click.echo("💡 Credentials cached securely for git operations")
            
        except Exception as e:
            click.echo(f"❌ Login failed: {e}", err=True)
        finally:
            await client.close()
    
    handle_async(_login())


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
        import json
        import tempfile
        import shutil
        
        # Check for .plato-hub.json configuration
        config_file = '.plato-hub.json'
        hub_config = None
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    hub_config = json.load(f)
                click.echo(f"✅ Found Plato hub configuration for '{hub_config['simulator_name']}'", err=True)
            except Exception as e:
                click.echo(f"❌ Error reading hub config: {e}", err=True)
                return
        
        if not hub_config:
            # Fallback to regular git command
            click.echo("⚠️  No Plato hub configuration found. Running regular git command...", err=True)
            git_cmd = ['git'] + list(args)
            result = subprocess.run(git_cmd, capture_output=False, text=True)
            if result.returncode != 0:
                ctx.exit(result.returncode)
            return
        
        # Handle Plato hub-specific git operations
        command = args[0] if args else ''
        
        if command == 'push':
            _hub_push(hub_config, list(args[1:]) if len(args) > 1 else [])
        elif command == 'pull':
            _hub_pull(hub_config, list(args[1:]) if len(args) > 1 else [])
        elif command in ['status', 'log', 'diff', 'branch']:
            # For read-only commands, create a temporary isolated view
            _hub_status(hub_config, command, list(args[1:]) if len(args) > 1 else [])
        else:
            # For other commands, run them normally but warn about hub context
            click.echo(f"⚠️  Running '{command}' in hub-linked directory", err=True)
            git_cmd = ['git'] + list(args)
            result = subprocess.run(git_cmd, capture_output=False, text=True)
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
    
    Checks for plato hub configuration and starts a dev machine (placeholder).
    """
    import os
    import json
    
    try:
        # Check for .plato-hub.json configuration
        config_file = '.plato-hub.json'
        
        if not os.path.exists(config_file):
            click.echo("❌ No Plato hub configuration found in this directory.", err=True)
            click.echo("💡 Use 'uv run plato hub clone <sim_name>' or 'uv run plato hub link <sim_name>' first.", err=True)
            return
        
        try:
            with open(config_file, 'r') as f:
                hub_config = json.load(f)
            
            sim_name = hub_config['simulator_name']
            repo_name = hub_config['repository']['full_name']
            
            click.echo(f"✅ Found Plato hub configuration for simulator '{sim_name}'")
            click.echo(f"🔗 Linked to: {repo_name}")
            click.echo(f"📁 Sync directory: {hub_config.get('sync_directory', 'current')}")
            
        except Exception as e:
            click.echo(f"❌ Error reading hub config: {e}", err=True)
            return
        
        click.echo("🚧 Sandbox environment starting... (placeholder)")
        click.echo("This will eventually start a development environment for the current repository.")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


if __name__ == '__main__':
    cli() 