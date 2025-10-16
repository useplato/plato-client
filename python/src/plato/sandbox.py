import os
import shutil
import tempfile
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from plato.sdk import Plato
from plato.sandbox_sdk import PlatoSandboxSDK
from pydantic import BaseModel
import json
import yaml
import subprocess
import base64
import time
from plato.models.build_models import (
    SimConfig,
    SimConfigDataset,
    SimConfigCompute,
    SimConfigMetadata,
    SimConfigService,
)
from plato.hub import copy_files_respecting_gitignore


class Repository(BaseModel):
    name: str
    full_name: str
    clone_url: str
    description: str


class PlatoHubConfig(BaseModel):
    simulator_name: str
    simulator_id: int
    repository: Repository
    sync_directory: str


class SandboxInfo(BaseModel):
    public_id: str
    job_group_id: str
    service: str
    commit_hash: str
    dataset: str
    dataset_config: SimConfigDataset
    url: str
    ssh_url: str
    local_port: int
    ssh_host: str


class InitVMInfo(BaseModel):
    vm_job_uuid: str
    correlation_id: str
    url: str
    job_group_id: str


class SSHExecutionResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    event_data: Dict[str, Any]
    error: Optional[str] = None


def get_authenticated_url(hub_config: PlatoHubConfig) -> str:
    """Get authenticated clone URL using cached credentials"""
    try:
        # Check for cached credentials
        cache_dir = os.path.expanduser("~/.plato-hub")
        cache_file = os.path.join(cache_dir, "credentials.json")

        if not os.path.exists(cache_file):
            raise Exception("No cached credentials found")

        with open(cache_file, "r") as f:
            credentials = json.load(f)

        base_url = hub_config.repository.clone_url
        username = credentials.get("username")
        password = credentials.get("password")

        if username and password and base_url.startswith("https://"):
            return base_url.replace("https://", f"https://{username}:{password}@")
        else:
            raise Exception("No cached credentials found")
    except Exception as e:
        raise Exception(
            f"Error getting authenticated url, try running 'uv run plato hub login' first: {e}"
        )


# =============================================================================
# SSH Config Utilities
# =============================================================================


def read_ssh_config() -> str:
    """Read SSH config file, return empty string if doesn't exist."""
    ssh_config_path = os.path.join(os.path.expanduser("~/.ssh"), "config")
    if os.path.exists(ssh_config_path):
        with open(ssh_config_path, "r") as f:
            return f.read()
    return ""


def host_exists_in_config(hostname: str, config_content: str) -> bool:
    """Check if a hostname exists in SSH config."""
    return f"Host {hostname}" in config_content


def find_available_hostname(base_hostname: str, config_content: str) -> str:
    """Find next available hostname by appending numbers if needed."""
    hostname = base_hostname
    counter = 1

    while host_exists_in_config(hostname, config_content):
        hostname = f"{base_hostname}-{counter}"
        counter += 1

    return hostname


def remove_ssh_host_from_config(hostname: str, config_content: str) -> str:
    """Remove a host entry from SSH config content."""
    lines = config_content.split("\n")
    new_lines = []
    skip_block = False

    for line in lines:
        if line.strip() == f"Host {hostname}":
            skip_block = True
            continue
        elif line.startswith("Host ") and skip_block:
            skip_block = False
            new_lines.append(line)
        elif not skip_block:
            new_lines.append(line)

    return "\n".join(new_lines).rstrip()


def write_ssh_config(config_content: str) -> None:
    """Write SSH config content to file."""
    ssh_config_dir = os.path.expanduser("~/.ssh")
    os.makedirs(ssh_config_dir, exist_ok=True)
    ssh_config_path = os.path.join(ssh_config_dir, "config")

    with open(ssh_config_path, "w") as f:
        if config_content:
            f.write(config_content)
            if not config_content.endswith("\n"):
                f.write("\n")


def append_ssh_host_entry(
    hostname: str, port: int, key_path: str, job_group_id: str
) -> None:
    """Append a new SSH host entry to config."""
    config_content = read_ssh_config()

    proxytunnel_path = shutil.which("proxytunnel")

    config_with_proxy = f"""Host {hostname}
    HostName localhost
    Port {port}
    User root
    IdentityFile {key_path}
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ConnectTimeout 10
    ProxyCommand {proxytunnel_path} -E -p proxy.plato.so:9000 -P '{job_group_id}@22:newpass' -d %h:%p --no-check-certificate
    ServerAliveInterval 30
    ServerAliveCountMax 3
    TCPKeepAlive yes
    """

    if config_content:
        config_content = config_content.rstrip() + "\n\n" + config_with_proxy
    else:
        config_content = config_with_proxy

    write_ssh_config(config_content)


class Sandbox:
    def __init__(self):
        self.sandbox_info = None
        self._vm_job_uuid: Optional[str] = None

    async def init(
        self,
        console: Console,
        dataset: str,
        plato_client: Plato,
        plato_sandbox_sdk: PlatoSandboxSDK,
    ):
        self.console = console
        self.dataset = dataset
        self.client = plato_client
        self.sandbox_sdk = plato_sandbox_sdk

        public_id = None

        try:
            # Debug: show SDK target and key presence
            try:
                self.console.print(
                    f"[dim]DEBUG: SandboxSDK base_url={getattr(plato_sandbox_sdk, 'base_url', 'unknown')} api_key_set={'yes' if getattr(plato_sandbox_sdk, 'api_key', None) else 'no'}[/dim]"
                )
            except Exception:
                pass
            ## Step 1: Load hub configuration ##
            hub_config_file = ".plato-hub.json"
            if not os.path.exists(hub_config_file):
                self.console.print(
                    "❌ No Plato hub configuration found in this directory."
                )
                self.console.print(
                    "💡 Use 'uv run plato hub clone <sim_name>' or 'uv run plato hub link <sim_name>' first."
                )
                return
            try:
                with open(hub_config_file, "r") as f:
                    hub_config = json.load(f)
                hub_cfg_obj = PlatoHubConfig.model_validate(hub_config)
                sim_name = hub_cfg_obj.simulator_name
            except Exception as e:
                self.console.print(f"[red]❌ Error reading hub config: {e}")
                return

            sim_panel = Panel.fit(
                f"[green]✅ Found Plato simulator[/green]\n"
                f"[cyan]Name:[/cyan] {sim_name}",
                title="[bold green]✅ Simulator[/bold green]",
                border_style="green",
            )
            self.console.print(sim_panel)

            ## Step 2: Load simulator configuration ##
            sim_config_file = "./plato-config.yml"
            print(f"Sim config file: {sim_config_file}")
            if os.path.exists(sim_config_file):
                try:
                    with open(sim_config_file, "r") as f:
                        raw_cfg = yaml.safe_load(f)
                        print(f"Raw config: {raw_cfg}")
                    # Validate into SimConfig model to ensure attribute access like .datasets
                    sim_config = SimConfig.model_validate(raw_cfg)
                    print(f"Sim config: {sim_config}")
                except Exception as e:
                    self.console.print(
                        f"[yellow]⚠️  Could not load {sim_config_file}: {e}"
                    )

            else:
                self.console.print(
                    f"[yellow]⚠️  No {sim_config_file} found in current directory"
                )

                if Confirm.ask(
                    "💡 Would you like to create a default plato-config.yml file?",
                    default=True,
                ):
                    sim_config = SimConfig(
                        datasets={
                            self.dataset: SimConfigDataset(
                                compute=SimConfigCompute(),
                                metadata=SimConfigMetadata(),
                                services={
                                    "main_app": SimConfigService(type="docker-compose")
                                },
                                listeners={},
                            )
                        }
                    )
                    with open(sim_config_file, "w") as f:
                        yaml.dump(sim_config.model_dump(), f)
                    message = (
                        "Default plato-config.yml created, run again with edited config"
                    )
                if not message:
                    message = (
                        "No plato-config.yml found, please run again with proper config"
                    )
                raise Exception(message)

            cfg_panel = Panel.fit(
                f"[green]✅ Configuration loaded/created[/green]\n"
                f"[cyan]File:[/cyan] {sim_config_file}",
                title="[bold green]✅ Config Loaded/Created[/bold green]",
                border_style="green",
            )
            self.console.print(cfg_panel)

            ## Step 3: Extract the dataset configuration ##
            dataset_config = sim_config.datasets[self.dataset]
            resources_panel = Panel.fit(
                f"💻 CPUs: {dataset_config.compute.cpus}, Memory: {dataset_config.compute.memory}MB, Disk: {dataset_config.compute.disk}MB\n"
                f"🔗 App port: {dataset_config.compute.app_port}, Messaging port: {dataset_config.compute.plato_messaging_port}\n"
                f"📊 Dataset: {self.dataset}",
                title="[bold cyan]📋 Resources[/bold cyan]",
                border_style="cyan",
            )
            self.console.print(resources_panel)

            ## Step 4: Force push to main and save commit hash ##
            clone_url = get_authenticated_url(hub_cfg_obj)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                current_dir = os.getcwd()
                subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                os.chdir(temp_repo)
                # Copy files respecting .gitignore
                copy_files_respecting_gitignore(
                    current_dir, ".", exclude_files=[".plato-hub.json"]
                )
                subprocess.run(["git", "add", "."], capture_output=True)
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        "Development snapshot for sandbox",
                    ],
                    capture_output=True,
                )
                # Get commit hash before pushing
                commit_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commit_hash = commit_result.stdout.strip()

                subprocess.run(
                    ["git", "push", "--force", "origin", "main"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                os.chdir(current_dir)
            commit_panel = Panel.fit(
                f"[green]✅ Force pushed to main branch[/green]\n"
                f"[cyan]Commit hash:[/cyan] {commit_hash}",
                title="[bold green]✅ Code Pushed[/bold green]",
                border_style="green",
            )
            self.console.print(commit_panel)

            ## Step 5: Start VM with progress tracking ##
            from rich.progress import (
                Progress as _Progress,
                SpinnerColumn as _SpinnerColumn,
                TextColumn as _TextColumn,
            )

            with _Progress(
                _SpinnerColumn(),
                _TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as _progress:
                _task = _progress.add_task("[cyan]Starting VM...", total=None)
                try:
                    self.console.print(
                        f"[dim]DEBUG: create_vm(service={sim_name}, dataset={dataset}, cpus={dataset_config.compute.cpus}, mem={dataset_config.compute.memory}, disk={dataset_config.compute.disk})[/dim]"
                    )
                except Exception:
                    pass
                # Submit VM creation and monitor for completion
                vm_timeout = int(os.getenv("PLATO_SANDBOX_VM_TIMEOUT_SECS", "1200"))
                vm_wait = int(os.getenv("PLATO_SANDBOX_VM_WAIT_SECS", "600"))

                # Submit VM creation request
                vm_submit = await self.sandbox_sdk.create_vm(
                    sim_name,
                    dataset_config,
                    commit_hash,
                    dataset,
                    vm_timeout,
                    vm_wait,
                    "sandbox",
                )

                # Monitor VM creation for completion
                vm_result = await self._monitor_ssh_execution_with_data(
                    self.client,
                    vm_submit.correlation_id,
                    "VM Creation",
                    timeout=vm_timeout + 15,
                )

                if not vm_result.success:
                    error_msg = vm_result.error or "Unknown error"
                    raise Exception(f"VM creation failed: {error_msg}")

                # Use the VM info from the initial response
                vm_info = vm_submit
                try:
                    self.console.print(
                        f"[dim]DEBUG: create_vm response public_id={vm_info.public_id} job_group_id={vm_info.job_group_id} url={vm_info.url} corr={vm_info.correlation_id}[/dim]"
                    )
                except Exception:
                    pass
                _progress.update(_task, description="[green]VM started[/green]")
            public_id = vm_info.public_id
            self._vm_job_uuid = public_id
            vm_panel = Panel.fit(
                f"[green]Virtual machine is now running![/green]\n"
                f"[dim]UUID: {public_id}[/dim]\n"
                f"[dim]URL: {vm_info.url}[/dim]",
                title="[bold green]🟢 VM Startup Complete[/bold green]",
                border_style="green",
            )
            self.console.print(vm_panel)

            ## Step 6: Setup Local SSH Key ##
            local_key_path, local_public_key = await self._setup_local_ssh_key()
            ssh_panel = Panel.fit(
                f"[green]SSH key pair generated successfully![/green]\n"
                f"[cyan]Path:[/cyan] {local_key_path}",
                title="[bold green]✅ SSH Key Pair Generated[/bold green]",
                border_style="green",
            )
            self.console.print(ssh_panel)

            ## Step 7: Setup sandbox environment ##
            from rich.progress import (
                Progress as _Progress2,
                SpinnerColumn as _SpinnerColumn2,
                TextColumn as _TextColumn2,
            )

            with _Progress2(
                _SpinnerColumn2(),
                _TextColumn2("[progress.description]{task.description}"),
                console=self.console,
            ) as _progress2:
                _task2 = _progress2.add_task(
                    "[cyan]Setting up sandbox on VM...", total=None
                )
                try:
                    self.console.print(
                        f"[dim]DEBUG: setup_sandbox(public_id={public_id})[/dim]"
                    )
                except Exception:
                    pass

                # Submit sandbox setup request
                sandbox_submit = await self.sandbox_sdk.setup_sandbox(
                    public_id=public_id,
                    clone_url=clone_url,
                    dataset=dataset,
                    dataset_config=dataset_config,
                    local_public_key=local_public_key,
                )

                # Monitor sandbox setup for completion
                setup_result = await self._monitor_ssh_execution_with_data(
                    self.client,
                    sandbox_submit.correlation_id,
                    "Sandbox Setup",
                    timeout=600,  # 10 minutes for sandbox setup
                )

                if not setup_result.success:
                    error_msg = setup_result.error or "Unknown error"
                    raise Exception(f"Sandbox setup failed: {error_msg}")

                # Use the sandbox info from the initial response
                sandbox_info = sandbox_submit
                try:
                    self.console.print(
                        f"[dim]DEBUG: setup_sandbox ssh_url={sandbox_info.ssh_url} corr={sandbox_info.correlation_id}[/dim]"
                    )
                except Exception:
                    pass
                _progress2.update(
                    _task2, description="[green]Sandbox configured[/green]"
                )
            sandbox_panel = Panel.fit(
                f"[green]🎉 Your development sandbox is now fully operational![/green]\n"
                f"[cyan]• SSH URL:[/cyan] {sandbox_info.ssh_url}\n"
                f"[cyan]• Code location:[/cyan] [bold]/opt/plato[/bold]\n"
                f"[cyan]• Git hash:[/cyan] [bold]{commit_hash}[/bold]",
                title="[bold green]🚀 Sandbox Ready[/bold green]",
                border_style="green",
            )
            self.console.print(sandbox_panel)

            # choose a random port between 2200 and 2299
            import random

            local_port = random.randint(2200, 2299)

            ## Step 8: Setup SSH config ##
            ssh_host = await self._setup_ssh_config_with_password(
                local_port, vm_info.job_group_id
            )
            ssh_success_panel = Panel.fit(
                f"[green]SSH configuration updated successfully![/green]\n"
                f"[cyan]Connection command:[/cyan] [bold]ssh {ssh_host}[/bold]\n"
                f"[yellow]🔑 Uses SSH key authentication (passwordless)[/yellow]\n"
                f"[blue]📁 Remote path: /opt/plato[/blue]",
                title="[bold green]✅ SSH Ready[/bold green]",
                border_style="green",
            )
            self.console.print(ssh_success_panel)
            self.sandbox_info = SandboxInfo(
                public_id=public_id,
                job_group_id=vm_info.job_group_id,
                service=sim_name,
                commit_hash=commit_hash,
                dataset=dataset,
                dataset_config=dataset_config,
                url=vm_info.url,
                ssh_url=sandbox_info.ssh_url,
                local_port=local_port,
                ssh_host=ssh_host,
            )

        except Exception as e:
            raise e

    async def _reload_dataset_config(self) -> None:
        if not self.sandbox_info:
            raise Exception("Sandbox not initialized")
        sim_config_file = "plato-config.yml"
        if os.path.exists(sim_config_file):
            try:
                with open(sim_config_file, "r") as f:
                    raw_cfg = yaml.safe_load(f)
                # Validate into SimConfig model to ensure attribute access like .datasets
                sim_config = SimConfig.model_validate(raw_cfg)
            except Exception as e:
                raise Exception(f"Error loading plato-config.yml on reload: {e}")
        if not sim_config.datasets[self.dataset]:
            raise Exception(
                f"Dataset {self.dataset} not found in plato-config.yml, did you remove the current dataset from the config?"
            )
        if (
            sim_config.datasets[self.dataset].compute
            != self.sandbox_info.dataset_config.compute
        ):
            raise Exception(
                f"Compute configuration for dataset {self.dataset} does not match the sandbox config, did you change the compute configuration? Restart the sandbox to apply the new config."
            )
        self.sandbox_info.dataset_config = sim_config.datasets[self.dataset]

    async def _monitor_ssh_execution(
        self,
        client: "Plato",
        correlation_id: str,
        operation_name: str,
        timeout: int = 600,
    ) -> bool:
        try:
            result = await self._monitor_ssh_execution_with_data(
                client, correlation_id, operation_name, timeout
            )
            return result.success
        except Exception as e:
            raise Exception(f"Error monitoring {operation_name}: {e}")
            return False

    async def _monitor_ssh_execution_with_data(
        self,
        client: "Plato",
        correlation_id: str,
        operation_name: str,
        timeout: int = 600,
    ) -> SSHExecutionResult:
        def _filter_ssh_warnings(stderr: str) -> str:
            if not stderr:
                return ""
            lines = stderr.strip().split("\n")
            filtered_lines = []
            for line in lines:
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

        start_time = time.time()
        try:
            async with client.http_session.get(
                f"{client.base_url}/public-build/events/{correlation_id}",
                headers={"X-API-Key": client.api_key},
            ) as response:
                if response.status != 200:
                    raise Exception(
                        f"Failed to connect to event stream: {response.status}"
                    )

                async for line in response.content:
                    if time.time() - start_time > timeout:
                        raise Exception(f"Operation timed out after {timeout} seconds")

                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        try:
                            encoded_data = line_str[6:]
                            decoded_data = base64.b64decode(encoded_data).decode(
                                "utf-8"
                            )
                            self.console.print(f"🔗 Decoded data: {decoded_data}")
                            event_data = __import__("json").loads(decoded_data)
                            event_type = event_data.get("event_type", "unknown")

                            if event_type == "completed":
                                # Handle null values from snapshot operations
                                stdout = event_data.get("stdout") or ""
                                stderr = event_data.get("stderr") or ""

                                # Show only the final success line from stdout if available
                                if stdout and "✅" in stdout:
                                    success_lines = [
                                        line
                                        for line in stdout.strip().split("\n")
                                        if "✅" in line
                                    ]
                                    if success_lines:
                                        self.console.print(f"   {success_lines[-1]}")

                                # Show only important errors (filtered)
                                if stderr:
                                    filtered_stderr = _filter_ssh_warnings(stderr)
                                    if filtered_stderr and filtered_stderr.strip():
                                        error_lines = [
                                            line
                                            for line in filtered_stderr.strip().split(
                                                "\n"
                                            )
                                            if line.strip()
                                            and not line.startswith("Warning:")
                                        ]
                                        if error_lines:
                                            self.console.print(
                                                "📤 [yellow]Errors:[/yellow]"
                                            )
                                            for line in error_lines:
                                                self.console.print(f"   {line}")

                                return SSHExecutionResult(
                                    success=True,
                                    stdout=stdout,
                                    stderr=stderr,
                                    event_data=event_data,
                                )

                            elif event_type == "failed":
                                error = event_data.get("error", "Unknown error")
                                # Handle null values from snapshot operations
                                stdout = event_data.get("stdout") or ""
                                stderr = event_data.get("stderr") or ""
                                self.console.print(
                                    f"❌ [red]{operation_name} failed: {error}[/red]"
                                )
                                if stdout and stdout.strip():
                                    self.console.print(
                                        "📤 [yellow]Command Output:[/yellow]"
                                    )
                                    for line in stdout.strip().split("\n"):
                                        self.console.print(f"   {line}")
                                if stderr and stderr.strip():
                                    filtered_stderr = _filter_ssh_warnings(stderr)
                                    if filtered_stderr and filtered_stderr.strip():
                                        self.console.print(
                                            "📤 [red]Error Output:[/red]"
                                        )
                                        for line in filtered_stderr.strip().split("\n"):
                                            self.console.print(f"   {line}")

                                return SSHExecutionResult(
                                    success=False,
                                    stdout=stdout,
                                    stderr=stderr,
                                    event_data=event_data,
                                    error=error,
                                )
                        except Exception as e:
                            raise Exception(f"Error monitoring {operation_name}: {e}")
                            continue

        except Exception as e:
            raise Exception(f"Error monitoring {operation_name}: {e}")

        raise Exception(f"{operation_name} stream ended without completion")

    async def _setup_local_ssh_key(self) -> tuple[str, str]:
        import subprocess

        try:
            ssh_dir = os.path.expanduser("~/.ssh")
            os.makedirs(ssh_dir, exist_ok=True)
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
                os.chmod(local_key_path, 0o600)
                os.chmod(f"{local_key_path}.pub", 0o644)

            with open(f"{local_key_path}.pub", "r") as f:
                local_public_key = f.read().strip()

            return local_key_path, local_public_key
        except Exception as e:
            raise Exception(
                f"[yellow]⚠️  [yellow]Warning: Failed to setup SSH key: {e}[/yellow]"
            )

    async def _setup_ssh_config_with_password(
        self, local_port: int, job_group_id: str
    ) -> str:
        try:
            ssh_config_dir = os.path.expanduser("~/.ssh")
            os.makedirs(ssh_config_dir, exist_ok=True)
            key_path = os.path.join(ssh_config_dir, "plato_sandbox_key")

            # Find next available sandbox hostname using utility
            existing_config = read_ssh_config()
            ssh_host = find_available_hostname("sandbox", existing_config)

            # Add SSH host entry using utility
            append_ssh_host_entry(ssh_host, local_port, key_path, job_group_id)

            # No panels printed here; panels are printed by caller after completion
            return ssh_host
        except Exception as e:
            raise Exception(f"Failed to setup SSH config: {e}")

    async def close(self) -> None:
        # Delete SSH config entry if exists
        if self.sandbox_info and hasattr(self.sandbox_info, "ssh_host"):
            try:
                self.console.print(
                    f"🧹 Removing SSH config entry '{self.sandbox_info.ssh_host}'..."
                )

                # Read, remove host, and write back using utilities
                existing_config = read_ssh_config()
                if existing_config:
                    updated_config = remove_ssh_host_from_config(
                        self.sandbox_info.ssh_host, existing_config
                    )
                    write_ssh_config(updated_config)
                    self.console.print(
                        f"✅ SSH config entry '{self.sandbox_info.ssh_host}' removed"
                    )
            except Exception as e:
                # Non-fatal: log but continue with other cleanup
                self.console.print(
                    f"[yellow]⚠️  Failed to remove SSH config: {e}[/yellow]"
                )

        # Delete VM if exists
        vm_id = None
        if self.sandbox_info and getattr(self.sandbox_info, "public_id", None):
            vm_id = self.sandbox_info.public_id
        elif self._vm_job_uuid:
            vm_id = self._vm_job_uuid
        if vm_id:
            try:
                self.console.print("🧹 Cleaning up VM...")
                import asyncio as _asyncio
                from aiohttp import ClientTimeout as _ClientTimeout
                import signal as _signal

                async def _do_delete():
                    async with self.client.http_session.delete(
                        f"{self.client.base_url}/public-build/vm/{vm_id}",
                        headers={"X-API-Key": self.client.api_key},
                        timeout=_ClientTimeout(total=6),
                    ) as resp:
                        status = resp.status
                        body = None
                        try:
                            body = await resp.text()
                        except Exception:
                            body = None
                        return status, body

                # Temporarily ignore SIGINT so double Ctrl-C doesn't interrupt cleanup
                _prev = _signal.getsignal(_signal.SIGINT)
                try:
                    _signal.signal(_signal.SIGINT, _signal.SIG_IGN)
                    # Absolute guard: never wait longer than 5s total
                    status, body = await _asyncio.wait_for(
                        _asyncio.shield(_do_delete()), timeout=5
                    )
                finally:
                    try:
                        _signal.signal(_signal.SIGINT, _prev)
                    except Exception:
                        pass
                if 200 <= status < 300:
                    self.console.print("✅ VM cleaned up")
                else:
                    msg = body or ""
                    self.console.print(
                        f"[yellow]⚠️  VM cleanup responded with {status} {msg}"
                    )
            except _asyncio.TimeoutError:
                self.console.print(
                    "[yellow]⚠️  VM cleanup timed out; it will auto-expire shortly"
                )
            except KeyboardInterrupt:
                # Do not allow double Ctrl-C to suppress cleanup message
                self.console.print(
                    "[yellow]⚠️  Cleanup interrupted; VM will auto-expire shortly"
                )
            except Exception as cleanup_e:
                self.console.print(f"[yellow]⚠️  Failed to cleanup VM: {cleanup_e}")
        self._vm_job_uuid = None
