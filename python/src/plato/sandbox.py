import asyncio  # noqa: F401
import os
import shutil
import tempfile
from typing import Optional, Dict, Any

import typer  # noqa: F401
from rich.console import Console
from rich.table import Table  # noqa: F401
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from plato.sdk import Plato
from pydantic import BaseModel
import json
import yaml
import uuid
import subprocess
import base64
import time
import json  # noqa: F811
from plato.models.config import (
    SimConfig,
    SimConfigDataset,
    SimConfigCompute,
    SimConfigMetadata,
    SimConfigService,
)


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
    vm_job_uuid: str
    dev_branch: str
    vm_url: str
    ssh_url: str
    chisel_port: int
    local_port: int
    service: str
    ssh_host: str
    dataset: str
    dataset_config: SimConfigDataset


class InitVMInfo(BaseModel):
    vm_job_uuid: str
    correlation_id: str
    url: str


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


class Sandbox:
    def __init__(self):
        self.sandbox_info = None
        self._vm_job_uuid: Optional[str] = None
        self._chisel_process: Optional[subprocess.Popen] = None

    async def init(
        self, console: Console, dataset: str, plato_client: Plato, chisel_port: int
    ):
        self.console = console
        self.dataset = dataset
        self.client = plato_client

        vm_job_uuid = None

        try:
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

            ## Step 4: Create development branch ##
            branch_uuid = str(uuid.uuid4())[:8]
            dev_branch = f"dev-{branch_uuid}"

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
                subprocess.run(
                    ["git", "checkout", "-b", dev_branch],
                    capture_output=True,
                    check=True,
                )
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
            branch_panel = Panel.fit(
                f"[green]✅ Created and pushed development branch[/green]\n"
                f"[cyan]Branch:[/cyan] {dev_branch}",
                title="[bold green]✅ Branch Ready[/bold green]",
                border_style="green",
            )
            self.console.print(branch_panel)

            ## Step 5: Start VM with progress tracking ##
            vm_info = await self._init_vm(sim_name, dataset_config)
            vm_job_uuid = vm_info.vm_job_uuid
            self._vm_job_uuid = vm_job_uuid
            vm_panel = Panel.fit(
                f"[green]Virtual machine is now running![/green]\n"
                f"[dim]UUID: {vm_job_uuid}[/dim]\n"
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
            ssh_url = await self._init_vm_sandbox(
                vm_job_uuid,
                dev_branch,
                clone_url,
                chisel_port,
                local_public_key,
            )
            sandbox_panel = Panel.fit(
                f"[green]🎉 Your development sandbox is now fully operational![/green]\n"
                f"[cyan]• SSH URL:[/cyan] {ssh_url}\n"
                f"[cyan]• Code location:[/cyan] [bold]/opt/plato[/bold]\n"
                f"[cyan]• Development branch:[/cyan] [bold]{dev_branch}[/bold]",
                title="[bold green]🚀 Sandbox Ready[/bold green]",
                border_style="green",
            )
            self.console.print(sandbox_panel)

            ##  Step 8: Setup local chisel client ##
            local_port = await self._setup_chisel_client(ssh_url)
            tunnel_panel = Panel.fit(
                f"[green]Secure tunnel established successfully![/green]\n"
                f"[cyan]Local SSH port:[/cyan] [bold]{local_port}[/bold]\n"
                f"[dim]Your local machine can now connect securely to the remote sandbox[/dim]",
                title="[bold green]✅ Tunnel Active[/bold green]",
                border_style="green",
            )
            self.console.print(tunnel_panel)

            ## Step 9: Setup SSH config with password ##
            ssh_host = await self._setup_ssh_config_with_password(
                local_port, vm_job_uuid
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
                service=sim_name,
                vm_job_uuid=vm_job_uuid,
                dev_branch=dev_branch,
                vm_url=vm_info.url,
                ssh_url=ssh_url,
                chisel_port=chisel_port,
                local_port=local_port,
                ssh_host=ssh_host,
                dataset=dataset,
                dataset_config=dataset_config,
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

    async def snapshot(
        self, service: str, version: str, dataset: str, snapshot_name: str
    ):
        try:
            if not self.sandbox_info:
                raise Exception("Sandbox not initialized")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=False,
            ) as progress:
                overall_task = progress.add_task(
                    "[bold blue]📸 Creating VM snapshot...", total=100
                )

                # Build request and submit
                progress.update(
                    overall_task,
                    advance=0,
                    description="[bold blue]📸 Submitting snapshot request...",
                )

                snapshot_request = {
                    "service": service,
                    "version": version,
                    "dataset": dataset,
                    "timeout": 1800,
                }
                if snapshot_name:
                    snapshot_request["snapshot_name"] = snapshot_name

                self.console.print(f"📋 [cyan]Snapshot details:[/cyan]")
                self.console.print(f"  • Service: {service}")
                self.console.print(f"  • Version: {version}")
                self.console.print(f"  • Dataset: {dataset}")
                if snapshot_name:
                    self.console.print(f"  • Name: {snapshot_name}")
                self.console.print(f"  • Timeout: 1800 seconds")

                snapshot_response = await self.client.http_session.post(
                    f"{self.client.base_url}/public-build/vm/{self.sandbox_info.vm_job_uuid}/snapshot",
                    json=snapshot_request,
                    headers={"X-API-Key": self.client.api_key},
                )

                if snapshot_response.status == 200:
                    response_data = await snapshot_response.json()
                    progress.update(
                        overall_task,
                        advance=10,
                        description="[bold green] Snapshot request submitted...",
                    )

                    self.console.print(f"🔗 [cyan]Snapshot request submitted:[/cyan] {response_data}")  

                    correlation_id = response_data.get("correlation_id")
                    if correlation_id:
                        self.console.print(
                            f"🔗 Monitoring via SSE: {self.client.base_url}/public-build/events/{correlation_id}"
                        )
                        success = await self._monitor_ssh_execution(
                            self.client,
                            correlation_id,
                            "VM snapshot creation",
                            timeout=1800,
                        )
                        if success:
                            progress.update(
                                overall_task,
                                advance=90,
                                description="[bold green]✅ Snapshot created successfully![/bold green]",
                            )
                        else:
                            progress.update(
                                overall_task,
                                completed=100,
                                description="[bold red]❌ Snapshot creation failed or timed out[/bold red]",
                            )
                            raise Exception("Snapshot creation failed or timed out")
                    else:
                        progress.update(
                            overall_task,
                            completed=100,
                            description="[bold red]❌ No correlation_id received from snapshot response[/bold red]",
                        )
                        raise Exception(
                            "No correlation_id received from snapshot response"
                        )
                else:
                    error = await snapshot_response.text()
                    progress.update(
                        overall_task,
                        completed=100,
                        description=f"[bold red]❌ API Error: Failed to create snapshot: {error}[/bold red]",
                    )
                    raise Exception(f"API Error: Failed to create snapshot: {error}")
        except Exception as e:
            raise Exception(f"Error creating snapshot: {e}")

    async def backup(self):
        try:
            if not self.sandbox_info:
                raise Exception("Sandbox not initialized")

            self.console.print("📦 [cyan] Getting job group id for backup...[/cyan]")
            job_group_id = None
            job = await self.client.http_session.get(
                f"{self.client.base_url}/jobs/{self.sandbox_info.vm_job_uuid}",
                headers={"X-API-Key": self.client.api_key},
            )
            job_json = await job.json()
            job_group_id = job_json["job_group_id"]

            self.console.print("📦 [cyan]Creating environment backup...[/cyan]")

            backup_response = await self.client.http_session.post(
                f"{self.client.base_url}/env/{job_group_id}/backup",
                headers={"X-API-Key": self.client.api_key},
            )
            if backup_response.status == 200:
                backup_response_json = await backup_response.json()
                self.console.print(
                    f"✅ [green]Environment backup completed successfully[/green] {backup_response_json}"
                )
                return backup_response_json
            else:
                error = await backup_response.text()
                raise Exception(f"Failed to backup environment: {error}")
        except Exception as e:
            raise Exception(f"Error creating environment backup: {e}")

    async def reset(self):
        try:
            if not self.sandbox_info:
                raise Exception("Sandbox not initialized")

            self.console.print("📦 [cyan] Getting job group id for reset...[/cyan]")
            job_group_id = None
            job = await self.client.http_session.get(
                f"{self.client.base_url}/jobs/{self.sandbox_info.vm_job_uuid}",
                headers={"X-API-Key": self.client.api_key},
            )
            job_json = await job.json()
            job_group_id = job_json["job_group_id"]

            self.console.print("📦 [cyan]Creating environment reset...[/cyan]")

            reset_response = await self.client.http_session.post(
                f"{self.client.base_url}/env/{job_group_id}/reset",
                headers={"X-API-Key": self.client.api_key},
                json={"load_browser_state": False},
            )
            if reset_response.status == 200:
                reset_response_json = await reset_response.json()
                # Handle both dict and object responses - sorry for being an idiot and not handling this properly
                if isinstance(reset_response_json, dict):
                    success = reset_response_json.get('success', False)
                    error = reset_response_json.get('error')
                else:
                    success = getattr(reset_response_json, 'success', False)
                    error = getattr(reset_response_json, 'error', None)
                
                if success:
                    self.console.print(
                        f"✅ [green]Environment reset completed successfully[/green] {reset_response_json}"
                    )
                else:
                    raise Exception(f"Failed to reset environment: {error or 'Unknown error'}")
            else:
                error = await reset_response.text()
                raise Exception(f"Failed to reset environment: {error}")
        except Exception as e:
            raise Exception(f"Error creating environment reset: {e}")

    async def start_services(self, dataset: str, timeout: int) -> None:
        """Start simulator services using the existing docker-compose in the repository."""
        try:
            if not self.sandbox_info:
                raise Exception("Sandbox not initialized")

            await self._reload_dataset_config()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=False,
            ) as progress:
                overall_task = progress.add_task(
                    "[bold blue]🚀 Starting services...", total=100
                )
                progress.update(
                    overall_task,
                    advance=0,
                    description="[bold blue]🚀 Starting services...",
                )

                # Call the start-services endpoint with dataset + config
                services_response = await self.client.http_session.post(
                    f"{self.client.base_url}/public-build/vm/{self.sandbox_info.vm_job_uuid}/start-services",
                    json={
                        "dataset": dataset,
                        "plato_dataset_config": self.sandbox_info.dataset_config.model_dump(),
                        "timeout": timeout,
                    },
                    headers={"X-API-Key": self.client.api_key},
                )

                if services_response.status == 200:
                    response_data = await services_response.json()
                    progress.update(
                        overall_task,
                        advance=10,
                        description="[bold green] Services submitted...",
                    )
                    correlation_id = response_data.get("correlation_id")
                    if correlation_id:
                        success = await self._monitor_ssh_execution(
                            self.client,
                            correlation_id,
                            "Services startup",
                            timeout=timeout,
                        )
                        if success:
                            progress.update(
                                overall_task,
                                advance=100,
                                description="[bold green]✅ Services started successfully![/bold green]",
                            )
                        else:
                            progress.update(
                                overall_task,
                                advance=100,
                                description="[bold red]❌ Services startup failed or timed out[/bold red]",
                            )
                            raise Exception("Services startup failed or timed out")
                    else:
                        progress.update(
                            overall_task,
                            advance=100,
                            description="[bold red]❌ No correlation_id received from services response[/bold red]",
                        )
                        raise Exception(
                            "No correlation_id received from services response"
                        )
                else:
                    error = await services_response.text()
                    progress.update(
                        overall_task,
                        advance=100,
                        description=f"[bold red]❌ API Error: Failed to start services: {error}[/bold red]",
                    )
                return
        except Exception as e:
            raise Exception(f"Unknown error starting services: {e}")

    async def start_listeners(self, dataset: str, timeout: int = 600) -> None:
        """Start listeners and plato worker with the dataset configuration."""
        try:
            if not self.sandbox_info:
                raise Exception("Sandbox not initialized")

            await self._reload_dataset_config()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=False,
            ) as progress:
                overall_task = progress.add_task(
                    "[bold blue]🚀 Starting listeners...", total=100
                )
                progress.update(
                    overall_task,
                    advance=0,
                    description="[bold blue]🚀 Starting listeners...",
                )

                # start listeners request
                listeners_request = {
                    "plato_worker_version": "prod-latest",
                    "dataset": dataset,
                    "plato_dataset_config": self.sandbox_info.dataset_config.model_dump(),
                }
                listeners_response = await self.client.http_session.post(
                    f"{self.client.base_url}/public-build/vm/{self.sandbox_info.vm_job_uuid}/start-listeners",
                    json=listeners_request,
                    headers={"X-API-Key": self.client.api_key},
                )

                # check if listeners started successfully
                if listeners_response.status == 200:
                    response_data = await listeners_response.json()
                    progress.update(
                        overall_task,
                        advance=10,
                        description="[bold green] Listeners submitted...",
                    )
                    correlation_id = response_data.get("correlation_id")
                    if correlation_id:
                        success = await self._monitor_ssh_execution(
                            self.client,
                            correlation_id,
                            "Listeners startup",
                            timeout=timeout,
                        )
                        if success:
                            progress.update(
                                overall_task,
                                advance=100,
                                description="[bold green]✅ Listeners started successfully![/bold green]",
                            )
                        else:
                            progress.update(
                                overall_task,
                                advance=100,
                                description="[bold red]❌ Listeners startup failed or timed out[/bold red]",
                            )
                            raise Exception("Listeners startup failed or timed out")
                    else:
                        progress.update(
                            overall_task,
                            advance=100,
                            description="[bold red]❌ No correlation_id received from listeners response[/bold red]",
                        )
                        raise Exception(
                            "No correlation_id received from listeners response"
                        )
                else:
                    error = await listeners_response.text()
                    progress.update(
                        overall_task,
                        advance=100,
                        description=f"[bold red]❌ API Error: Failed to start listeners: {error}[/bold red]",
                    )
                return
        except Exception as e:
            raise Exception(f"Unknown error starting listeners: {e}")

    async def _init_vm(
        self, sim_name: str, dataset_config: SimConfigDataset
    ) -> InitVMInfo:
        """Initialize VM with integrated progress tracking and startup monitoring."""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=False,
        ) as progress:
            overall_task = progress.add_task(
                "[bold blue]🚀 Starting sandbox VM...", total=100
            )

            # Step 1: Create VM instance (20% of progress)
            progress.update(
                overall_task,
                advance=20,
                description="[bold blue]🚀 Creating VM instance...",
            )

            try:
                vm_response = await self.client.http_session.post(
                    f"{self.client.base_url}/public-build/vm/create",
                    json={
                        "service": sim_name,
                        "version": "sandbox",
                        "plato_dataset_config": dataset_config.model_dump(mode="json"),
                        "wait_time": 120,
                        "vm_timeout": 1800,
                        "alias": f"{sim_name}-sandbox",
                    },
                    headers={"X-API-Key": self.client.api_key},
                )

                if vm_response.status != 200:
                    error = await vm_response.text()
                    raise Exception(f"Failed to create VM: {error}")

                vm_info = await vm_response.json()
                vm_job_uuid = vm_info["uuid"]
                correlation_id = vm_info["correlation_id"]

            except Exception as e:
                raise Exception(f"Error creating VM: {e}")

            # Step 2: Wait for VM startup (70% of progress)
            progress.update(
                overall_task,
                advance=10,
                description="[bold yellow]⏳ Waiting for VM startup...",
            )

            # Monitor VM startup with progress updates
            start_time = time.time()
            timeout = 1800
            startup_progress = 30  # Start at 30% total progress

            try:
                async with self.client.http_session.get(
                    f"{self.client.base_url}/public-build/events/{correlation_id}",
                    headers={"X-API-Key": self.client.api_key},
                ) as response:
                    if response.status != 200:
                        raise Exception(
                            f"Failed to connect to event stream: {response.status}"
                        )

                    async for line in response.content:
                        if time.time() - start_time > timeout:
                            raise Exception(
                                f"VM startup timed out after {timeout} seconds"
                            )

                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            try:
                                encoded_data = line_str[6:]
                                decoded_data = base64.b64decode(encoded_data).decode(
                                    "utf-8"
                                )
                                event_data = json.loads(decoded_data)

                                if event_data.get("event_type") == "completed":
                                    # Complete the progress bar
                                    progress.update(
                                        overall_task,
                                        completed=100,
                                        description="[bold green]✅ VM startup complete!",
                                    )

                                    break
                                elif event_data.get("event_type") == "failed":
                                    error = event_data.get("error", "Unknown error")
                                    raise Exception(f"VM startup failed: {error}")
                                else:
                                    # Update progress incrementally during startup
                                    message = event_data.get("message", "")
                                    if message:
                                        # Gradually increase progress during startup phase
                                        if startup_progress < 90:
                                            startup_progress += 2
                                            progress.update(
                                                overall_task,
                                                completed=startup_progress,
                                                description=f"[bold yellow]⏳ {message}...",
                                            )

                                        # Only show significant startup events
                                        if any(
                                            keyword in message.lower()
                                            for keyword in [
                                                "starting",
                                                "initializing",
                                                "ready",
                                                "allocated",
                                                "configured",
                                            ]
                                        ):
                                            self.console.print(
                                                f"[dim]  {message}[/dim]"
                                            )

                            except Exception:
                                # Skip malformed events
                                continue

            except Exception as e:
                raise Exception(f"Error waiting for VM: {e}")

            # No panels printed here; panels are printed by caller after completion

            return InitVMInfo(
                vm_job_uuid=vm_job_uuid,
                correlation_id=correlation_id,
                url=vm_info["url"],
            )

    async def _init_vm_sandbox(
        self,
        vm_job_uuid: str,
        dev_branch: str,
        clone_url: str,
        chisel_port: int,
        local_public_key: str,
    ) -> str:
        """Initialize sandbox environment with integrated progress tracking."""
        import base64
        import time
        import json

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=False,
            ) as progress:
                overall_task = progress.add_task(
                    "[bold blue]🔧 Setting up sandbox environment...", total=100
                )

                # Step 1: Send setup request (20% of progress)
                progress.update(
                    overall_task,
                    advance=20,
                    description="[bold blue]🔧 Sending setup request...",
                )

                setup_data = {
                    "branch": dev_branch,
                    "clone_url": clone_url,
                    "chisel_port": chisel_port,
                    "timeout": 300,
                }
                if local_public_key:
                    setup_data["client_ssh_public_key"] = local_public_key

                try:
                    setup_response = await self.client.http_session.post(
                        f"{self.client.base_url}/public-build/vm/{vm_job_uuid}/setup-sandbox",
                        json=setup_data,
                        headers={"X-API-Key": self.client.api_key},
                    )

                    if setup_response.status != 200:
                        error = await setup_response.text()
                        raise Exception(f"Failed to setup sandbox: {error}")

                    setup_response_data = await setup_response.json()
                    if not setup_response_data:
                        raise Exception("Failed to setup sandbox environment")

                    ssh_url = setup_response_data["ssh_url"]
                    # if running the api locally, replace the localhost:8080 with staging.plato.so
                    ssh_url = ssh_url.replace(
                        "http://localhost:8080", "https://staging.plato.so"
                    )
                    correlation_id = setup_response_data["correlation_id"]

                except Exception as e:
                    raise Exception(f"Error setting up sandbox: {e}")

                # Step 2: Monitor setup progress (70% of progress)
                progress.update(
                    overall_task,
                    advance=10,
                    description="[bold yellow]⏳ Monitoring sandbox setup...",
                )

                # Monitor sandbox setup with progress updates
                start_time = time.time()
                timeout = 600
                setup_progress = 30  # Start at 30% total progress

                try:
                    async with self.client.http_session.get(
                        f"{self.client.base_url}/public-build/events/{correlation_id}",
                        headers={"X-API-Key": self.client.api_key},
                    ) as response:
                        if response.status != 200:
                            raise Exception(
                                f"Failed to connect to setup stream: {response.status}"
                            )

                        async for line in response.content:
                            if time.time() - start_time > timeout:
                                raise Exception(
                                    f"Sandbox setup timed out after {timeout} seconds"
                                )

                            line_str = line.decode("utf-8").strip()
                            if line_str.startswith("data: "):
                                try:
                                    encoded_data = line_str[6:]
                                    decoded_data = base64.b64decode(
                                        encoded_data
                                    ).decode("utf-8")
                                    event_data = json.loads(decoded_data)

                                    if event_data.get("event_type") == "completed":
                                        # Complete the progress bar
                                        progress.update(
                                            overall_task,
                                            completed=100,
                                            description="[bold green]✅ Sandbox setup complete!",
                                        )
                                        # Sub-step completion log in gray
                                        self.console.print(
                                            "[dim]  ✅ Sandbox setup complete![/dim]"
                                        )
                                        break
                                    elif event_data.get("event_type") == "failed":
                                        error = event_data.get("error", "Unknown error")
                                        message = event_data.get("message", "")
                                        # Handle null values
                                        stdout = event_data.get("stdout") or ""
                                        stderr = event_data.get("stderr") or ""

                                        error_details = f"Sandbox setup failed: {error}"
                                        if message:
                                            error_details += f" (Step: {message})"
                                        if stdout and stdout.strip():
                                            error_details += (
                                                f" | Output: {stdout.strip()}"
                                            )
                                        if stderr and stderr.strip():
                                            error_details += (
                                                f" | Error: {stderr.strip()}"
                                            )

                                        raise Exception(error_details)
                                    else:
                                        # Update progress incrementally during setup
                                        message = event_data.get("message", "")
                                        if message:
                                            # Gradually increase progress during setup phase
                                            if setup_progress < 90:
                                                setup_progress += 3
                                                progress.update(
                                                    overall_task,
                                                    completed=setup_progress,
                                                    description=f"[bold yellow]🔧 {message}...",
                                                )

                                            # Only show significant setup events
                                            if any(
                                                keyword in message.lower()
                                                for keyword in [
                                                    "cloning",
                                                    "installing",
                                                    "configuring",
                                                    "starting",
                                                    "ready",
                                                    "completed",
                                                ]
                                            ):
                                                self.console.print(
                                                    f"[dim]  {message}[/dim]"
                                                )

                                except Exception:
                                    # Skip malformed events
                                    continue

                except Exception as e:
                    raise Exception(f"Error monitoring sandbox setup: {e}")

                # No panels printed here; panels are printed by caller after completion

                return ssh_url

        except Exception as e:
            # Re-raise with clean error message for higher-level handling
            raise Exception(str(e))

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
        import base64
        import time

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
                                    success_lines = [line for line in stdout.strip().split("\n") if "✅" in line]
                                    if success_lines:
                                        self.console.print(f"   {success_lines[-1]}")

                                # Show only important errors (filtered)
                                if stderr:
                                    filtered_stderr = _filter_ssh_warnings(stderr)
                                    if filtered_stderr and filtered_stderr.strip():
                                        error_lines = [line for line in filtered_stderr.strip().split("\n") if line.strip() and not line.startswith("Warning:")]
                                        if error_lines:
                                            self.console.print("📤 [yellow]Errors:[/yellow]")
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

    async def _setup_chisel_client(self, ssh_url: str) -> int:
        import subprocess
        import random
        import time

        try:
            chisel_path = shutil.which("chisel")
            if not chisel_path:
                self.console.print("📦 Installing chisel client...")
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
                        check=False,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    raise Exception(
                        "Failed to install chisel. Please install manually."
                    )
                except FileNotFoundError:
                    raise Exception("curl not found. Please install chisel manually.")
            if "/connect-job/" not in ssh_url:
                raise Exception(f"Invalid SSH URL format: {ssh_url}")
            url_parts = ssh_url.split("/connect-job/")
            base_url = url_parts[0].replace("https://", "").replace("http://", "")
            server_url = f"{base_url}"
            if "localhost" in base_url:
                server_url = server_url.replace("localhost", "127.0.0.1")
            local_ssh_port = random.randint(2200, 2299)
            chisel_cmd = ["chisel", "client", ssh_url, f"{local_ssh_port}:127.0.0.1:22"]
            # No panels printed here; panels are printed by caller after completion
            chisel_process = subprocess.Popen(
                chisel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self._chisel_process = chisel_process
            time.sleep(3)
            if chisel_process.poll() is None:
                # No panels printed here; panels are printed by caller after completion
                return local_ssh_port
            else:
                stdout, stderr = chisel_process.communicate()
                raise Exception(f"Chisel client failed: {stderr.decode()}")
        except Exception as e:
            raise Exception(f"Error setting up chisel: {e}")

    async def _setup_ssh_config_with_password(
        self, local_port: int, vm_job_uuid: str
    ) -> str:
        try:
            ssh_config_dir = os.path.expanduser("~/.ssh")
            os.makedirs(ssh_config_dir, exist_ok=True)
            key_path = os.path.join(ssh_config_dir, "plato_sandbox_key")
            ssh_host = f"plato-sandbox-{vm_job_uuid[:8]}"
            config_entry = (
                f"Host {ssh_host}\n"
                f"\tHostName localhost\n"
                f"\tPort {local_port}\n"
                f"\tUser root\n"
                f"\tIdentityFile {key_path}\n"
                f"\tIdentitiesOnly yes\n"
                f"\tStrictHostKeyChecking no\n"
                f"\tUserKnownHostsFile /dev/null\n"
                f"\tConnectTimeout 10\n\n"
            )
            ssh_config_path = os.path.join(ssh_config_dir, "config")
            existing_config = ""
            if os.path.exists(ssh_config_path):
                with open(ssh_config_path, "r") as f:
                    existing_config = f.read()
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
            with open(ssh_config_path, "w") as f:
                if existing_config:
                    f.write(existing_config.rstrip())
                    f.write("\n\n")  # Ensure proper spacing between entries
                f.write(config_entry)
            # No panels printed here; panels are printed by caller after completion
            return ssh_host
        except Exception as e:
            raise Exception(f"Failed to setup SSH config: {e}")

    async def close(self) -> None:
        # Never raise from cleanup; make idempotent
        # Stop chisel client if running
        if self._chisel_process and self._chisel_process.poll() is None:
            try:
                self._chisel_process.terminate()
                try:
                    self._chisel_process.wait(timeout=5)
                except Exception:
                    self._chisel_process.kill()
            except Exception:
                pass
        self._chisel_process = None

        # Delete VM if exists
        vm_id = None
        if self.sandbox_info and getattr(self.sandbox_info, "vm_job_uuid", None):
            vm_id = self.sandbox_info.vm_job_uuid
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
