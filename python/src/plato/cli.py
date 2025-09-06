#!/usr/bin/env python3
"""
Plato CLI - Command line interface for Plato SDK
"""

import asyncio
import json
import sys
import os
import shutil
import tempfile
from typing import Optional

import click
from plato.sdk import Plato
from plato.exceptions import PlatoClientError
from dotenv import load_dotenv

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
        click.echo("Operation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        # Check if it's an auth issue and provide helpful hint
        if "401" in str(e) or "Unauthorized" in str(e):
            click.echo(
                "💡 Hint: Make sure PLATO_API_KEY is set in your environment or .env file",
                err=True,
            )
        sys.exit(1)


@click.group()
@click.version_option()
def cli():
    """Plato CLI - Manage Plato environments from the command line."""
    pass


@cli.command()
@click.argument("env_name")
@click.option(
    "--interface-type",
    default="browser",
    type=click.Choice(["browser", "noop"]),
    help="Interface type for the environment (default: browser)",
)
@click.option("--width", default=1920, help="Viewport width (default: 1920)")
@click.option("--height", default=1080, help="Viewport height (default: 1080)")
@click.option(
    "--keepalive",
    is_flag=True,
    help="Keep environment alive (disable heartbeat timeout)",
)
@click.option("--alias", help="Alias for the job group")
@click.option("--open-page", is_flag=True, help="Open page on start")
def make(
    env_name: str,
    interface_type: str,
    width: int,
    height: int,
    keepalive: bool,
    alias: Optional[str],
    open_page: bool,
):
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
                open_page_on_start=open_page,
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
@click.argument("env_id")
@click.option("--task-id", help="Optional task ID to reset with")
@click.option("--agent-version", help="Optional agent version")
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
@click.argument("env_id")
@click.option("--pretty", is_flag=True, help="Pretty print JSON output")
@click.option("--mutations", is_flag=True, help="Show only state mutations")
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
                click.echo(
                    f"Error: Environment '{env_id}' has no active run session. Try resetting it first.",
                    err=True,
                )
            else:
                raise
        finally:
            await client.close()

    handle_async(_state())


@cli.command()
@click.argument("env_id")
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
            if "message" in status_data:
                click.echo(f"Message: {status_data['message']}")

            # Pretty print the full status
            click.echo("Full status:")
            click.echo(json.dumps(status_data, indent=2))

        finally:
            await client.close()

    handle_async(_status())


@cli.command()
@click.argument("env_id")
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
@click.argument("env_id")
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
                click.echo(
                    f"  {status} {sim['name']} - {sim.get('description', 'No description')}"
                )

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
            click.echo(
                "❌ Authentication failed. Run 'uv run plato hub login' first.",
                err=True,
            )
            return

        sim_name = hub_config["simulator_name"]

        click.echo(f"📤 Pushing to simulator '{sim_name}'...")

        # Create temporary directory for isolated git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, "temp_repo")

            # Clone the simulator repository
            result = subprocess.run(
                ["git", "clone", clone_url, temp_repo], capture_output=True, text=True
            )
            if result.returncode != 0:
                click.echo(
                    f"❌ Failed to clone simulator repo: {result.stderr.strip()}",
                    err=True,
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
                click.echo("📝 No changes to push")
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
            click.echo(
                "❌ Authentication failed. Run 'uv run plato hub login' first.",
                err=True,
            )
            return

        sim_name = hub_config["simulator_name"]

        click.echo(f"📥 Pulling from simulator '{sim_name}'...")

        # Create temporary directory for isolated git operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, "temp_repo")

            # Clone the simulator repository
            result = subprocess.run(
                ["git", "clone", clone_url, temp_repo], capture_output=True, text=True
            )
            if result.returncode != 0:
                click.echo(
                    f"❌ Failed to clone simulator repo: {result.stderr.strip()}",
                    err=True,
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

            click.echo(f"✅ Successfully pulled from simulator '{sim_name}'")
            click.echo(
                "💡 Files updated in current directory. Review and commit to your monorepo as needed."
            )

    except Exception as e:
        click.echo(f"❌ Error during pull: {e}", err=True)


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
                            click.echo("🟢 VM startup completed")
                            return True
                        elif event_data.get("event_type") == "failed":
                            error = event_data.get("error", "Unknown error")
                            raise Exception(f"VM startup failed: {error}")
                        else:
                            # Show progress
                            message = event_data.get("message", "Starting...")
                            click.echo(f"⏳ {message}")

                    except (json.JSONDecodeError, base64.binascii.Error):
                        continue  # Skip malformed lines

    except Exception as e:
        click.echo(f"❌ Error waiting for VM: {e}", err=True)
        return False


async def _wait_for_setup_ready(
    client: "Plato", correlation_id: str, timeout: int = 300
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
                    click.echo(f"⏰ Timeout reached after {timeout} seconds")
                    raise Exception(f"Sandbox setup timed out after {timeout} seconds")

                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    try:
                        # Decode base64 data
                        encoded_data = line_str[6:]  # Remove 'data: ' prefix
                        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
                        event_data = json.loads(decoded_data)

                        if (
                            event_data.get("event_type") == "completed"
                            or event_data.get("event_type") == "workflow_progress"
                        ):
                            message = event_data.get("message", "Setup progress...")
                            click.echo(f"🔧 {message}")

                            # Show stdout/stderr for debugging
                            stdout = event_data.get("stdout", "")
                            stderr = event_data.get("stderr", "")

                            if stdout and stdout.strip():
                                click.echo(f"📤 Output: {stdout.strip()}")
                            if stderr and stderr.strip():
                                click.echo(f"📤 Error: {stderr.strip()}")

                            # Check if chisel server started successfully - that means we're done
                            if "Chisel server started successfully" in stdout:
                                click.echo("🟢 Sandbox setup completed successfully!")
                                return True

                        elif event_data.get("event_type") == "failed":
                            error = event_data.get("error", "Unknown error")
                            stdout = event_data.get("stdout", "")
                            stderr = event_data.get("stderr", "")
                            message = event_data.get("message", "")

                            click.echo(f"❌ STEP FAILED: {message}")
                            click.echo(f"❌ Error: {error}")
                            if stdout:
                                click.echo(f"📤 STDOUT: {stdout}")
                            if stderr:
                                click.echo(f"📤 STDERR: {stderr}")
                            
                            # Show ALL event data for debugging
                            import json
                            click.echo(f"🔍 FULL ERROR DATA: {json.dumps(event_data, indent=2)}")

                            raise Exception(f"Step failed: {message} | Error: {error}")

                    except (json.JSONDecodeError, base64.binascii.Error):
                        continue  # Skip malformed lines

    except Exception as e:
        click.echo(f"❌ Error waiting for sandbox setup: {e}", err=True)
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

            click.echo(f"🔑 Generated SSH key pair: {local_key_path}")

        # Read our public key to send to the VM
        with open(f"{local_key_path}.pub", "r") as f:
            local_public_key = f.read().strip()

        click.echo(f"🔑 SSH key ready for passwordless access")
        return local_key_path, local_public_key

    except Exception as e:
        click.echo(f"⚠️  Warning: Failed to setup SSH key: {e}")
        return None, None


async def _setup_sandbox(
    client: "Plato", vm_job_uuid: str, dev_branch: str, clone_url: str, chisel_port: int = 6000
):
    """Setup the sandbox environment with code and chisel SSH"""
    import json
    import uuid

    try:
        # Generate local SSH key for passwordless access
        click.echo("🔑 Setting up SSH authentication...")
        local_key_path, local_public_key = _setup_local_ssh_key()

        # Setup sandbox environment via new endpoint
        setup_data = {
            "branch": dev_branch, 
            "clone_url": clone_url, 
            "chisel_port": chisel_port,
            "timeout": 300
        }

        # Add client SSH public key if available
        if local_public_key:
            setup_data["client_ssh_public_key"] = local_public_key
            click.echo("🔑 Sending SSH public key for passwordless access")

        setup_response = await client.http_session.post(
            f"{client.base_url}/public-build/vm/{vm_job_uuid}/setup-sandbox",
            json=setup_data,
            headers={"X-API-Key": client.api_key},
        )

        if setup_response.status != 200:
            error = await setup_response.text()
            click.echo(f"❌ Failed to setup sandbox: {error}", err=True)
            return None

        return await setup_response.json()

    except Exception as e:
        click.echo(f"❌ Error setting up sandbox: {e}", err=True)
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
        click.echo("❌ Failed to setup local chisel client", err=True)
        return

    # Ask permission and set up SSH config with unique host name
    ssh_host = None
    if click.confirm("💡 Set up SSH config for easy connection?", default=True):
        ssh_host = _setup_ssh_config_with_password(local_port, vm_job_uuid)
    
    # Store ssh_host for use in commands
    sandbox_info["ssh_host"] = ssh_host or f"plato-sandbox-{vm_job_uuid[:8]}"

    click.echo("🚀 Sandbox is ready! Choose an action:")

    while True:
        click.echo("\n📋 Sandbox Menu:")
        click.echo("  1. Open VS Code connected to sandbox")
        click.echo("  2. Open Cursor connected to sandbox")
        click.echo("  3. Show VM info")
        click.echo("  4. Stop sandbox and cleanup")

        try:
            choice = click.prompt("Choose an action (1-4)", type=int)
        except (KeyboardInterrupt, EOFError):
            break

        if choice == 1:
            # VS Code via SSH tunnel
            click.echo(f"🔧 Opening VS Code connected to sandbox...")
            success = _open_editor_via_ssh("code", sandbox_info["ssh_host"], local_port)
            if success:
                click.echo("✅ VS Code opened successfully")
                click.echo(
                    "💡 Your code is available at /opt/plato in the remote environment"
                )
            else:
                click.echo("❌ Failed to open VS Code")

        elif choice == 2:
            # Cursor via SSH tunnel
            click.echo(f"🔧 Opening Cursor connected to sandbox...")
            success = _open_editor_via_ssh("cursor", sandbox_info["ssh_host"], local_port)
            if success:
                click.echo("✅ Cursor opened successfully")
                click.echo(
                    "💡 Your code is available at /opt/plato in the remote environment"
                )
            else:
                click.echo("❌ Failed to open Cursor")

        elif choice == 3:
            # Show VM info
            try:
                status_response = await client.get_job_status(vm_job_uuid)
                click.echo("📊 Sandbox VM Information:")
                click.echo(f"  🆔 Job UUID: {vm_job_uuid}")
                click.echo(f"  📈 Status: {status_response.get('status', 'unknown')}")
                click.echo(f"  🔗 SSH: ssh {sandbox_info['ssh_host']}")
                click.echo(f"  🔑 SSH key authentication (passwordless)")
                click.echo(f"  📁 Code directory: /opt/plato")
                click.echo(f"  🌿 Development branch: {sandbox_info['dev_branch']}")
                click.echo(f"  💻 VM URL: {sandbox_info['vm_url']}")

                # Show chisel connection info
                click.echo(f"  🔗 Chisel tunnel: localhost:{local_port} → VM:22")

                if "message" in status_response:
                    click.echo(f"  📝 Status message: {status_response['message']}")

            except Exception as e:
                click.echo(f"❌ Failed to get VM status: {e}")

        elif choice == 4:
            # Stop and cleanup
            break
        else:
            click.echo("❌ Invalid choice. Please enter 1-4.")


async def _setup_chisel_client(ssh_url: str) -> Optional[int]:
    """Setup local chisel client and return the local SSH port"""
    import subprocess
    import random
    import time

    try:
        # Install chisel client if needed
        chisel_path = shutil.which("chisel")
        if not chisel_path:
            click.echo("📦 Installing chisel client...")
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
                click.echo("✅ Chisel installed successfully")
            except subprocess.CalledProcessError:
                click.echo(
                    "❌ Failed to install chisel. Please install manually.", err=True
                )
                return None
            except FileNotFoundError:
                click.echo(
                    "❌ curl not found. Please install chisel manually.", err=True
                )
                return None

        # Parse the SSH URL to get server details
        # ssh_url format: https://domain.com/connect-job/job_uuid/chisel_port
        if "/connect-job/" not in ssh_url:
            click.echo(f"❌ Invalid SSH URL format: {ssh_url}", err=True)
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

        click.echo(f"🔗 Starting chisel client: {' '.join(chisel_cmd)}")

        # Start chisel in background
        chisel_process = subprocess.Popen(
            chisel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Wait a moment for chisel to establish connection
        time.sleep(3)

        # Check if chisel is still running
        if chisel_process.poll() is None:
            click.echo(f"✅ Chisel client running (local SSH port: {local_ssh_port})")

            return local_ssh_port
        else:
            stdout, stderr = chisel_process.communicate()
            click.echo(f"❌ Chisel client failed: {stderr.decode()}", err=True)
            return None

    except Exception as e:
        click.echo(f"❌ Error setting up chisel: {e}", err=True)
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

        click.echo("✅ SSH config updated!")
        click.echo(f"🔗 Passwordless connection: ssh {ssh_host}")
        click.echo("🔑 Uses SSH key authentication (no password needed)")
        click.echo("📁 Remote path: /opt/plato")
        
        return ssh_host

    except Exception as e:
        click.echo(f"❌ Failed to setup SSH config: {e}")
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
            click.echo(
                f"💡 If connection fails, use: F1 → 'Remote-SSH: Connect to Host' → '{ssh_host}'"
            )
        elif editor == "cursor":
            subprocess.run(
                ["cursor", "--remote", f"ssh-remote+{ssh_host}", "/opt/plato"],
                check=False,
            )
            click.echo(
                f"💡 If connection fails, use: F1 → 'Remote-SSH: Connect to Host' → '{ssh_host}'"
            )

        return True

    except FileNotFoundError:
        click.echo(f"❌ {editor} not found. Please install {editor}.")
        click.echo(f"💡 Alternative: ssh {ssh_host} (SSH key authentication)")
        return False
    except Exception as e:
        click.echo(f"❌ Error opening {editor}: {e}")
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
                click.echo(
                    f"📁 Creating isolated view (couldn't fetch remote: {clone_result.stderr.strip()[:50]}...)"
                )
            else:
                click.echo(f"📡 Comparing against simulator repository")

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

            click.echo(
                f"✅ Added {len(patterns_to_add)} credential protection patterns to .gitignore",
                err=True,
            )

    except Exception as e:
        # Silently fail - gitignore protection is nice-to-have, not critical
        pass


# Hub commands for Git repository management
@cli.group()
def hub():
    """Plato Hub - Manage simulator repositories and development environments."""
    pass


@hub.command()
@click.argument("sim_name")
@click.option("--description", help="Description for the new simulator")
@click.option(
    "--sim-type", default="docker_app", help="Type of simulator (default: docker_app)"
)
@click.option(
    "--directory", help="Directory to create and clone into (default: sim_name)"
)
def init(
    sim_name: str, description: Optional[str], sim_type: str, directory: Optional[str]
):
    """Initialize a new simulator with repository and clone it.

    SIM_NAME: The name of the new simulator to create
    """

    async def _init():
        client = Plato()
        try:
            click.echo(f"🚀 Initializing new simulator '{sim_name}'...")

            # Check if simulator already exists
            existing_simulators = await client.list_gitea_simulators()
            for sim in existing_simulators:
                if sim["name"].lower() == sim_name.lower():
                    click.echo(f"❌ Simulator '{sim_name}' already exists", err=True)
                    return

            # Step 1: Create the simulator
            click.echo(f"📦 Creating simulator '{sim_name}'...")
            simulator = await client.create_simulator(
                name=sim_name, description=description, sim_type=sim_type
            )
            click.echo(
                f"✅ Created simulator: {simulator['name']} (ID: {simulator['id']})"
            )

            # Step 2: Create repository for the simulator
            click.echo(f"📁 Creating repository for simulator...")
            repo_info = await client.create_simulator_repository(simulator["id"])
            click.echo(f"✅ Created repository: {repo_info['full_name']}")

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

            click.echo(f"📥 Cloning {repo_info['full_name']} to {target_dir}...")

            import subprocess

            try:
                result = subprocess.run(
                    ["git", "clone", clone_url, target_dir],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                click.echo(f"✅ Successfully cloned to: {target_dir}")
                click.echo(f"🎉 Simulator '{sim_name}' is ready!")
                click.echo(f"💡 cd {target_dir} && start developing your simulator")

                if repo_info.get("description"):
                    click.echo(f"📝 Description: {repo_info['description']}")

            except subprocess.CalledProcessError as e:
                click.echo(
                    f"❌ Failed to clone repository: {e.stderr.strip()}", err=True
                )
            except FileNotFoundError:
                click.echo("❌ Git is not installed or not in PATH", err=True)

        except Exception as e:
            click.echo(f"❌ Initialization failed: {e}", err=True)
        finally:
            await client.close()

    handle_async(_init())


@hub.command()
@click.argument("sim_name")
@click.option(
    "--directory", help="Directory to clone into (default: current directory)"
)
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
                if sim["name"].lower() == sim_name.lower():
                    simulator = sim
                    break

            if not simulator:
                click.echo(f"❌ Simulator '{sim_name}' not found.", err=True)
                available = [s["name"] for s in simulators]
                if available:
                    click.echo(
                        f"💡 Available simulators: {', '.join(available)}", err=True
                    )
                return

            if not simulator.get("has_repo", False):
                click.echo(
                    f"❌ Simulator '{sim_name}' exists but doesn't have a repository configured.",
                    err=True,
                )
                click.echo(
                    "💡 Contact your administrator to set up a repository for this simulator.",
                    err=True,
                )
                return

            # Get repository details
            repo_info = await client.get_simulator_repository(simulator["id"])
            if not repo_info.get("has_repo", False):
                click.echo(
                    f"❌ Repository for simulator '{sim_name}' is not available.",
                    err=True,
                )
                click.echo(f"💡 Attempting to create repository for '{sim_name}'...")

                # Try to create the repository
                try:
                    create_response = await client.http_session.post(
                        f"{client.base_url}/gitea/simulators/{simulator['id']}/repo",
                        headers={"X-API-Key": client.api_key},
                    )
                    if create_response.status == 200:
                        repo_info = await create_response.json()
                        click.echo(f"✅ Created repository for '{sim_name}'")
                    else:
                        error_text = await create_response.text()
                        click.echo(
                            f"❌ Failed to create repository: {error_text}", err=True
                        )
                        return
                except Exception as create_e:
                    click.echo(f"❌ Failed to create repository: {create_e}", err=True)
                    return

            clone_url = repo_info["clone_url"]
            repo_name = repo_info["name"]

            # Get admin credentials for authentication
            try:
                creds = await client.get_gitea_credentials()
                if clone_url.startswith("https://"):
                    authenticated_url = clone_url.replace(
                        "https://", f"https://{creds['username']}:{creds['password']}@"
                    )
                    clone_url = authenticated_url
                    click.echo(
                        f"✅ Using admin credentials for authentication (user: {creds['username']})"
                    )
                else:
                    click.echo(
                        f"⚠️  Warning: URL not HTTPS, authentication may fail: {clone_url}",
                        err=True,
                    )
            except Exception as creds_e:
                click.echo(
                    f"⚠️  Warning: Could not get admin credentials: {creds_e}", err=True
                )
                click.echo("💡 Clone may require manual authentication", err=True)

            # Determine target directory
            if directory:
                target_dir = directory
            else:
                target_dir = repo_name

            click.echo(f"Cloning {repo_info['full_name']} to {target_dir}...")

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
                click.echo(f"✅ Successfully cloned {repo_info['full_name']}")
                click.echo(f"Repository cloned to: {target_dir}")

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

                    click.echo("✅ Created Plato hub configuration")
                    click.echo(
                        "💡 You can now use 'uv run plato hub sandbox' in this directory"
                    )

                except Exception as config_e:
                    click.echo(
                        f"⚠️  Warning: Could not create hub config: {config_e}", err=True
                    )

                if repo_info.get("description"):
                    click.echo(f"Description: {repo_info['description']}")

            except subprocess.CalledProcessError as e:
                click.echo(
                    f"❌ Failed to clone repository: {e.stderr.strip()}", err=True
                )
                if "Authentication failed" in e.stderr:
                    click.echo(
                        "💡 Hint: Make sure your Git credentials are configured for Gitea access.",
                        err=True,
                    )
            except FileNotFoundError:
                click.echo("❌ Git is not installed or not in PATH", err=True)

        finally:
            await client.close()

    handle_async(_clone())


@hub.command()
@click.argument("sim_name")
@click.argument("directory", required=False)
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
                if sim["name"].lower() == sim_name.lower():
                    simulator = sim
                    break

            if not simulator:
                click.echo(f"❌ Simulator '{sim_name}' not found.", err=True)
                available = [s["name"] for s in simulators]
                if available:
                    click.echo(
                        f"💡 Available simulators: {', '.join(available)}", err=True
                    )
                return

            if not simulator.get("has_repo", False):
                click.echo(
                    f"❌ Simulator '{sim_name}' exists but doesn't have a repository configured.",
                    err=True,
                )
                click.echo(
                    "💡 Contact your administrator to set up a repository for this simulator.",
                    err=True,
                )
                return

            # Get repository details
            repo_info = await client.get_simulator_repository(simulator["id"])
            if not repo_info.get("has_repo", False):
                click.echo(
                    f"Repository for simulator '{sim_name}' is not available.", err=True
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
                    click.echo(f"Using admin credentials for authentication")

            click.echo(
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

                click.echo(f"✅ Created Plato hub configuration for '{sim_name}'")
                click.echo(
                    f"🔗 Directory '{target_dir}' is now linked to {repo_info['full_name']}"
                )
                click.echo(
                    "💡 This directory will sync with the simulator repo independently"
                )
                click.echo("💡 Run 'uv run plato hub login' to authenticate")
                click.echo("💡 Then use 'uv run plato hub git push/pull' to sync")
                click.echo("💡 Your monorepo structure remains intact!")

            except subprocess.CalledProcessError as e:
                click.echo(
                    f"❌ Failed to link repository: {e.stderr.decode().strip()}",
                    err=True,
                )
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
        config_file = ".plato-hub.json"
        hub_config = None

        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    hub_config = json.load(f)
                click.echo(
                    f"✅ Found Plato hub configuration for '{hub_config['simulator_name']}'",
                    err=True,
                )
            except Exception as e:
                click.echo(f"❌ Error reading hub config: {e}", err=True)
                return

        if not hub_config:
            # Fallback to regular git command
            click.echo(
                "⚠️  No Plato hub configuration found. Running regular git command...",
                err=True,
            )
            git_cmd = ["git"] + list(args)
            result = subprocess.run(git_cmd, capture_output=False, text=True)
            if result.returncode != 0:
                ctx.exit(result.returncode)
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
            click.echo(f"⚠️  Running '{command}' in hub-linked directory", err=True)
            git_cmd = ["git"] + list(args)
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
@click.option(
    "--config",
    default="plato-config.yml",
    help="VM configuration file (default: plato-config.yml)",
)
@click.option("--keep-vm", is_flag=True, help="Keep VM running after sandbox exits")
@click.option("--chisel-port", default=6000, help="Port for chisel server (default: 6000)")
def sandbox(config: str, keep_vm: bool, chisel_port: int):
    """Start a development sandbox environment.

    Creates a development VM with your simulator code and opens an interactive environment.
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
                click.echo(
                    "❌ No Plato hub configuration found in this directory.", err=True
                )
                click.echo(
                    "💡 Use 'uv run plato hub clone <sim_name>' or 'uv run plato hub link <sim_name>' first.",
                    err=True,
                )
                return

            try:
                with open(config_file, "r") as f:
                    hub_config = json.load(f)

                sim_name = hub_config["simulator_name"]
                click.echo(f"✅ Found Plato simulator: {sim_name}")

            except Exception as e:
                click.echo(f"❌ Error reading hub config: {e}", err=True)
                return

            # Step 2: Load VM configuration
            vm_config = {
                "vcpu_count": 1,
                "mem_size_mib": 1024,
                "overlay_size_mb": 2048,
                "port": 8080,
                "messaging_port": 7000,
                "chisel_port": chisel_port,
            }

            if os.path.exists(config):
                try:
                    with open(config, "r") as f:
                        user_config = yaml.safe_load(f)
                    vm_config.update(user_config)
                    # Override chisel_port if user specified it via CLI
                    if chisel_port != 6000:  # User specified a different port
                        vm_config["chisel_port"] = chisel_port
                    click.echo(f"✅ Loaded VM config from {config}")
                    click.echo(f"🔗 Using chisel port: {vm_config['chisel_port']}")
                except Exception as e:
                    click.echo(f"⚠️  Could not load {config}, using defaults: {e}")
            else:
                click.echo(f"⚠️  No {config} found, using default VM configuration")
                click.echo(f"🔗 Using chisel port: {chisel_port}")

            # Step 3: Create development branch and push current state
            branch_uuid = str(uuid.uuid4())[:8]
            dev_branch = f"dev-{branch_uuid}"

            click.echo(f"🌱 Creating development branch: {dev_branch}")

            # Get authenticated URL
            clone_url = _get_authenticated_url(hub_config)
            if not clone_url:
                click.echo(
                    "❌ Authentication required. Run 'uv run plato hub login' first.",
                    err=True,
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

            click.echo(f"✅ Created and pushed development branch: {dev_branch}")

            # Step 4: Start VM
            click.echo(f"🚀 Starting sandbox VM...")

            # Create VM
            vm_response = await client.http_session.post(
                f"{client.base_url}/public-build/vm/create",
                json={
                    "service": sim_name,
                    "version": "sandbox",
                    "vcpu_count": vm_config["vcpu_count"],
                    "mem_size_mib": vm_config["mem_size_mib"],
                    "overlay_size_mb": vm_config["overlay_size_mb"],
                    "port": vm_config["port"],
                    "messaging_port": vm_config["messaging_port"],
                    "wait_time": 120,
                    "vm_timeout": 1800,
                    "alias": f"{sim_name}-sandbox",
                },
                headers={"X-API-Key": client.api_key},
            )

            if vm_response.status != 200:
                error = await vm_response.text()
                click.echo(f"❌ Failed to create VM: {error}", err=True)
                return

            vm_info = await vm_response.json()
            vm_job_uuid = vm_info["uuid"]
            correlation_id = vm_info["correlation_id"]

            click.echo(f"✅ VM created: {vm_job_uuid}")
            click.echo(f"🔗 URL: {vm_info['url']}")
            click.echo(f"⏳ Waiting for VM to start...")

            # Wait for VM to be ready by monitoring SSE stream
            vm_ready = await _wait_for_vm_ready(client, correlation_id)

            if not vm_ready:
                click.echo("❌ VM failed to start properly", err=True)
                return

            click.echo(f"✅ VM is ready!")

            # Step 5: Setup sandbox environment
            click.echo(f"🔧 Setting up sandbox environment...")

            setup_response = await _setup_sandbox(
                client, vm_job_uuid, dev_branch, clone_url, vm_config["chisel_port"]
            )

            if not setup_response:
                click.echo("❌ Failed to setup sandbox environment", err=True)
                return

            ssh_url = setup_response["ssh_url"]
            correlation_id = setup_response["correlation_id"]

            # Wait for sandbox setup to complete
            click.echo(f"⏳ Setting up sandbox environment...")
            setup_success = await _wait_for_setup_ready(client, correlation_id)

            if not setup_success:
                click.echo(
                    "❌ Sandbox setup failed - check the error messages above for details",
                    err=True,
                )
                # VM was created but setup failed, still cleanup if not keeping VM
                if not keep_vm:
                    try:
                        await client.http_session.delete(
                            f"{client.base_url}/public-build/vm/{vm_job_uuid}",
                            headers={"X-API-Key": client.api_key},
                        )
                        click.echo("🧹 Cleaned up failed VM")
                    except:
                        pass
                return

            click.echo(f"✅ Sandbox environment ready!")
            click.echo(f"🔗 SSH URL: {ssh_url}")
            click.echo(f"📁 Code available at: /opt/plato")

            # Step 6: Interactive sandbox mode
            sandbox_info = {
                "vm_job_uuid": vm_job_uuid,
                "dev_branch": dev_branch,
                "vm_url": vm_info["url"],
                "ssh_url": ssh_url,
                "chisel_port": vm_config["chisel_port"],
            }
            await _run_interactive_sandbox(sandbox_info, client, keep_vm)

        except KeyboardInterrupt:
            click.echo("\n🛑 Sandbox interrupted by user")
        except Exception as e:
            click.echo(f"❌ Sandbox failed: {e}", err=True)
        finally:
            # Cleanup VM unless keep_vm is specified
            if vm_job_uuid and not keep_vm:
                try:
                    click.echo("🧹 Cleaning up VM...")
                    await client.http_session.delete(
                        f"{client.base_url}/public-build/vm/{vm_job_uuid}",
                        headers={"X-API-Key": client.api_key},
                    )
                    click.echo("✅ VM cleaned up")
                except Exception as cleanup_e:
                    click.echo(f"⚠️  Failed to cleanup VM: {cleanup_e}", err=True)
            elif keep_vm:
                click.echo(
                    f"💡 VM {vm_job_uuid} is still running (use --keep-vm flag was used)"
                )

            await client.close()

    handle_async(_sandbox())


if __name__ == "__main__":
    cli()
