import asyncio
import os
import shutil
import tempfile
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel
import subprocess
import json
from plato.sdk import Plato
from pydantic import BaseModel


class InitSimulatorResult(BaseModel):
    success: bool
    directory: Optional[str] = None
    repo_full_name: Optional[str] = None
    error: Optional[str] = None


class CloneResult(BaseModel):
    success: bool
    directory: Optional[str] = None
    repo_full_name: Optional[str] = None
    simulator_id: Optional[int] = None
    error: Optional[str] = None


class LinkResult(BaseModel):
    success: bool
    repo_full_name: Optional[str] = None
    directory: Optional[str] = None
    error: Optional[str] = None


class AuthResult(BaseModel):
    success: bool
    username: Optional[str] = None
    org_name: Optional[str] = None
    error: Optional[str] = None


class GitResult(BaseModel):
    success: bool
    exit_code: Optional[int] = None
    error: Optional[str] = None


class Hub:
    """Service-style Hub with internal logging and structured results."""

    def __init__(self, sdk: Plato, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.sdk = sdk

    # ========== Small internal helpers (kept minimal) ==========
    def _get_authenticated_url(self, hub_config: dict) -> Optional[str]:
        import json

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

    def _ensure_gitignore_protects_credentials(self) -> None:
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"], capture_output=True
            )
            if result.returncode != 0:
                return
            root_result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
            )
            if root_result.returncode != 0:
                return
            git_root = root_result.stdout.strip()
            gitignore_path = os.path.join(git_root, ".gitignore")
            protect_patterns = [
                "# Plato hub credentials",
                "credentials.json",
                ".plato-hub/",
                "*.plato-hub.json",
            ]
            existing_content = ""
            if os.path.exists(gitignore_path):
                with open(gitignore_path, "r") as f:
                    existing_content = f.read()
            patterns_to_add = [p for p in protect_patterns if p not in existing_content]
            if patterns_to_add:
                with open(gitignore_path, "a") as f:
                    if existing_content and not existing_content.endswith("\n"):
                        f.write("\n")
                    f.write("\n".join(patterns_to_add) + "\n")
                self.console.print(
                    f"✅ Added {len(patterns_to_add)} credential protection patterns to .gitignore",
                )
        except Exception:
            pass

    # ========== Public commands ==========
    async def init_simulator(
        self,
        sim_name: str,
        description: Optional[str],
        sim_type: str,
        directory: Optional[str],
    ) -> InitSimulatorResult:
        """Create simulator + repo and clone it. Logs internally, returns structured result."""
        import subprocess

        try:
            self.console.print("[cyan]Checking existing simulators...[/cyan]")
            existing_simulators = await self.sdk.list_gitea_simulators()
            for sim in existing_simulators:
                if sim["name"].lower() == sim_name.lower():
                    msg = f"Simulator '{sim_name}' already exists"
                    self.console.print(f"[red]❌ {msg}[/red]")
                    return InitSimulatorResult(success=False, error=msg)

            self.console.print(f"[cyan]Creating simulator '{sim_name}'...[/cyan]")
            simulator = await self.sdk.create_simulator(
                name=sim_name, description=(description or ""), sim_type=sim_type
            )
            self.console.print(
                f"[green]✅ Created simulator: {simulator['name']} (ID: {simulator['id']})[/green]"
            )

            self.console.print("[cyan]Creating repository...[/cyan]")
            repo_info = await self.sdk.create_simulator_repository(simulator["id"])
            self.console.print(
                f"[green]✅ Created repository: {repo_info['full_name']}[/green]"
            )

            target_dir = directory or sim_name
            creds = await self.sdk.get_gitea_credentials()
            clone_url = repo_info["clone_url"]
            if clone_url.startswith("https://"):
                clone_url = clone_url.replace(
                    "https://", f"https://{creds['username']}:{creds['password']}@"
                )

            self.console.print(
                f"[cyan]Cloning {repo_info['full_name']} to {target_dir}...[/cyan]"
            )
            subprocess.run(
                ["git", "clone", clone_url, target_dir],
                capture_output=True,
                text=True,
                check=True,
            )

            self.console.print(
                Panel.fit(
                    f"[green]Simulator '{sim_name}' is ready![/green]\n"
                    f"[cyan]📁 Directory:[/cyan] [bold]{target_dir}[/bold]",
                    title="[bold green]🎉 Initialization Complete[/bold green]",
                    border_style="green",
                )
            )

            return InitSimulatorResult(
                success=True,
                directory=target_dir,
                repo_full_name=repo_info.get("full_name"),
            )

        except subprocess.CalledProcessError as e:
            err = f"Failed to clone repository: {e.stderr.strip()}"
            self.console.print(f"[red]❌ {err}[/red]")
            return InitSimulatorResult(success=False, error=err)
        except FileNotFoundError:
            err = "Git is not installed or not in PATH"
            self.console.print(f"[red]❌ {err}[/red]")
            return InitSimulatorResult(success=False, error=err)
        except Exception as e:
            err = f"Initialization failed: {e}"
            self.console.print(f"[red]❌ {err}[/red]")
            return InitSimulatorResult(success=False, error=err)

    async def clone_simulator(
        self, sim_name: str, directory: Optional[str]
    ) -> CloneResult:
        """Clone a simulator repository. Logs internally, returns structured result."""
        import subprocess
        import json

        try:
            self.console.print(f"Looking up simulator '{sim_name}'...")
            simulators = await self.sdk.list_gitea_simulators()
            simulator = next(
                (s for s in simulators if s["name"].lower() == sim_name.lower()),
                None,
            )
            if not simulator:
                available = (
                    ", ".join([s["name"] for s in simulators]) if simulators else "none"
                )
                msg = f"Simulator '{sim_name}' not found. Available: {available}"
                self.console.print(f"[red]❌ {msg}")
                return CloneResult(success=False, error=msg)

            if not simulator.get("has_repo", False):
                msg = "Simulator exists but doesn't have a repository configured."
                self.console.print(f"[red]❌ {msg}")
                return CloneResult(success=False, error=msg)

            repo_info = await self.sdk.get_simulator_repository(simulator["id"])
            if not repo_info.get("has_repo", False):
                self.console.print(
                    f"❌ Repository for simulator '{sim_name}' is not available."
                )
                self.console.print(
                    f"💡 Attempting to create repository for '{sim_name}'..."
                )
                create_response = await self.sdk.http_session.post(
                    f"{self.sdk.base_url}/gitea/simulators/{simulator['id']}/repo",
                    headers={"X-API-Key": self.sdk.api_key},
                )
                if create_response.status == 200:
                    repo_info = await create_response.json()
                    self.console.print(f"[green]✅ Created repository for '{sim_name}'")
                else:
                    error_text = await create_response.text()
                    msg = f"Failed to create repository: {error_text}"
                    self.console.print(f"[red]❌ {msg}")
                    return CloneResult(success=False, error=msg)

            clone_url = repo_info["clone_url"]
            repo_name = repo_info["name"]
            hub_config_for_auth = {"repository": {"clone_url": clone_url}}
            authenticated_clone_url = self._get_authenticated_url(hub_config_for_auth)
            if authenticated_clone_url:
                clone_url = authenticated_clone_url
                self.console.print("✅ Using cached credentials for authentication")
            else:
                msg = "No cached credentials found. Run 'plato hub login' first."
                self.console.print(f"[yellow]⚠️  {msg}")
                return CloneResult(success=False, error=msg)

            target_dir = directory or repo_name
            self.console.print(f"Cloning {repo_info['full_name']} to {target_dir}...")
            subprocess.run(
                ["git", "clone", clone_url, target_dir],
                capture_output=True,
                text=True,
                check=True,
            )

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
                    else repo_info["clone_url"],
                    "description": repo_info.get("description"),
                },
                "sync_directory": os.path.basename(target_dir),
            }
            config_path = os.path.join(target_dir, ".plato-hub.json")
            with open(config_path, "w") as f:
                json.dump(hub_config, f, indent=2)
            self.console.print("✅ Created Plato hub configuration")

            self.console.print(
                f"[green]✅ Successfully cloned {repo_info['full_name']}"
            )
            return CloneResult(
                success=True,
                directory=target_dir,
                repo_full_name=repo_info.get("full_name"),
                simulator_id=simulator.get("id"),
            )

        except subprocess.CalledProcessError as e:
            err = e.stderr.strip()
            self.console.print(f"❌ Failed to clone repository: {err}")
            if "Authentication failed" in err:
                self.console.print("🔧 Try running: plato hub login")
            return CloneResult(success=False, error=err)
        except FileNotFoundError:
            err = "Git is not installed or not in PATH"
            self.console.print(f"❌ {err}")
            return CloneResult(success=False, error=err)
        except Exception as e:
            err = str(e)
            self.console.print(f"❌ {err}")
            return CloneResult(success=False, error=err)

    async def link_directory(
        self, sim_name: str, directory: Optional[str]
    ) -> LinkResult:
        """Link a local directory to a simulator repository. Logs internally, returns structured result."""
        import json

        try:
            target_dir = directory or os.getcwd()
            self.console.print(f"Looking up simulator '{sim_name}'...")
            simulators = await self.sdk.list_gitea_simulators()
            simulator = next(
                (s for s in simulators if s["name"].lower() == sim_name.lower()),
                None,
            )
            if not simulator:
                available = (
                    ", ".join([s["name"] for s in simulators]) if simulators else "none"
                )
                msg = f"Simulator '{sim_name}' not found. Available: {available}"
                self.console.print(f"[red]❌ {msg}")
                return LinkResult(success=False, error=msg)

            if not simulator.get("has_repo", False):
                msg = "Simulator exists but doesn't have a repository configured."
                self.console.print(f"[red]❌ {msg}")
                return LinkResult(success=False, error=msg)

            repo_info = await self.sdk.get_simulator_repository(simulator["id"])
            if not repo_info.get("has_repo", False):
                msg = "Repository for simulator is not available."
                self.console.print(f"[red]❌ {msg}")
                return LinkResult(success=False, error=msg)

            clone_url = repo_info["clone_url"]
            if repo_info.get("admin_credentials") and clone_url.startswith("https://"):
                creds = repo_info["admin_credentials"]
                clone_url = clone_url.replace(
                    "https://", f"https://{creds['username']}:{creds['password']}@"
                )
                self.console.print("Using admin credentials for authentication")

            self.console.print(
                f"Linking directory '{target_dir}' to {repo_info['full_name']}..."
            )

            original_dir = os.getcwd()
            try:
                os.chdir(target_dir)
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
                        else repo_info["clone_url"],
                        "description": repo_info.get("description"),
                    },
                    "sync_directory": os.path.basename(target_dir),
                }
                config_file = os.path.join(target_dir, ".plato-hub.json")
                with open(config_file, "w") as f:
                    json.dump(hub_config, f, indent=2)
                self.console.print(
                    f"[green]✅ Created Plato hub configuration for '{sim_name}'"
                )
                self.console.print(
                    f"[green]🔗 Directory '{target_dir}' linked to {repo_info['full_name']}"
                )
            finally:
                os.chdir(original_dir)

            return LinkResult(
                success=True,
                repo_full_name=repo_info.get("full_name"),
                directory=target_dir,
            )

        except Exception as e:
            err = str(e)
            self.console.print(f"[red]❌ {err}")
            return LinkResult(success=False, error=err)

    async def authenticate(self) -> AuthResult:
        """Authenticate and cache credentials locally. Logs internally, returns structured result."""
        import json
        from datetime import datetime

        try:
            self.console.print("🔐 Authenticating with Plato hub...")
            creds = await self.sdk.get_gitea_credentials()
            cache_dir = os.path.expanduser("~/.plato-hub")
            os.makedirs(cache_dir, exist_ok=True)
            credentials = {
                "username": creds["username"],
                "password": creds["password"],
                "org_name": creds["org_name"],
                "cached_at": datetime.now().isoformat(),
            }
            cache_file = os.path.join(cache_dir, "credentials.json")
            with open(cache_file, "w") as f:
                json.dump(credentials, f, indent=2)
            os.chmod(cache_file, 0o600)
            self._ensure_gitignore_protects_credentials()
            self.console.print("✅ Credentials cached for git operations")

            return AuthResult(
                success=True,
                username=creds.get("username"),
                org_name=creds.get("org_name"),
            )
        except Exception as e:
            err = str(e)
            self.console.print(f"[red]❌ Login failed: {err}")
            return AuthResult(success=False, error=err)

    async def execute_git_command(self, args: List[str]) -> GitResult:
        """Execute git command in hub-linked directory. Logs internally, returns structured result."""
    

        try:
            if not args:
                self.console.print("❌ Please provide a git command")
                self.console.print("[yellow]💡 Example: plato hub git status[/yellow]")
                return GitResult(
                    success=False, exit_code=1, error="No command provided"
                )

            config_file = ".plato-hub.json"
            hub_config = None
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        hub_config = json.load(f)
                    self.console.print(
                        f"✅ Found Plato hub configuration for '{hub_config['simulator_name']}'",
                    )
                except Exception as e:
                    self.console.print(f"[red]❌ Error reading hub config: {e}")
                    return GitResult(success=False, exit_code=1, error=str(e))

            if not hub_config:
                self.console.print(
                    "⚠️  No Plato hub configuration found. Running regular git command..."
                )
                git_cmd = ["git"] + list(args)
                result = subprocess.run(git_cmd, capture_output=False, text=True)
                return GitResult(
                    success=result.returncode == 0, exit_code=result.returncode
                )

            command = args[0] if args else ""
            if command == "push":
                return await self._do_hub_push(
                    hub_config, list(args[1:]) if len(args) > 1 else []
                )
            elif command == "pull":
                return await self._do_hub_pull(
                    hub_config, list(args[1:]) if len(args) > 1 else []
                )
            elif command in ["status", "log", "diff", "branch"]:
                return await self._do_hub_status(
                    hub_config, command, list(args[1:]) if len(args) > 1 else []
                )
            else:
                self.console.print(
                    f"[yellow]⚠️  Running '{command}' in hub-linked directory"
                )
                git_cmd = ["git"] + list(args)
                result = subprocess.run(git_cmd, capture_output=False, text=True)
                return GitResult(
                    success=result.returncode == 0, exit_code=result.returncode
                )

        except FileNotFoundError:
            err = "Git is not installed or not in PATH"
            self.console.print("❌ Git is not installed or not in PATH")
            return GitResult(success=False, exit_code=1, error=err)
        except Exception as e:
            err = str(e)
            self.console.print(f"[red]❌ Error executing git command: {err}")
            return GitResult(success=False, exit_code=1, error=err)

    async def _do_hub_push(self, hub_config: dict, extra_args: List[str]) -> GitResult:
        import subprocess

        try:
            clone_url = self._get_authenticated_url(hub_config)
            if not clone_url:
                self.console.print(
                    "[red]❌ Authentication failed. Run 'plato hub login' first.[/red]"
                )
                return GitResult(success=False, exit_code=1, error="Auth required")
            sim_name = hub_config["simulator_name"]
            self.console.print(f"📤 Pushing to simulator '{sim_name}'...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                result = subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.console.print(
                        f"❌ Failed to clone simulator repo: {result.stderr.strip()}"
                    )
                    return GitResult(
                        success=False,
                        exit_code=result.returncode,
                        error=result.stderr.strip(),
                    )
                current_dir = os.getcwd()
                for item in os.listdir(current_dir):
                    if item.startswith("."):
                        continue
                    src = os.path.join(current_dir, item)
                    dst = os.path.join(temp_repo, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                os.chdir(temp_repo)
                subprocess.run(["git", "add", "."], check=True)
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"], capture_output=True, text=True
                )
                if not status_result.stdout.strip():
                    self.console.print("[yellow]📝 No changes to push[/yellow]")
                    return GitResult(success=True, exit_code=0)
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"Sync from {hub_config['sync_directory']} directory",
                    ],
                    check=True,
                )
                push_args = ["git", "push", "origin", "main"] + extra_args
                result = subprocess.run(push_args, capture_output=True, text=True)
                if result.returncode == 0:
                    self.console.print(
                        f"[green]✅ Successfully pushed to simulator '{sim_name}'"
                    )
                    return GitResult(success=True, exit_code=0)
                else:
                    self.console.print(f"[red]❌ Push failed: {result.stderr.strip()}")
                    return GitResult(
                        success=False,
                        exit_code=result.returncode,
                        error=result.stderr.strip(),
                    )
        except Exception as e:
            return GitResult(success=False, exit_code=1, error=str(e))

    async def _do_hub_pull(self, hub_config: dict, extra_args: List[str]) -> GitResult:
        import subprocess

        try:
            clone_url = self._get_authenticated_url(hub_config)
            if not clone_url:
                self.console.print(
                    "[red]❌ Authentication failed. Run 'plato hub login' first.[/red]"
                )
                return GitResult(success=False, exit_code=1, error="Auth required")
            sim_name = hub_config["simulator_name"]
            self.console.print(f"📥 Pulling from simulator '{sim_name}'...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                result = subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.console.print(
                        f"❌ Failed to clone simulator repo: {result.stderr.strip()}"
                    )
                    return GitResult(
                        success=False,
                        exit_code=result.returncode,
                        error=result.stderr.strip(),
                    )
                current_dir = os.getcwd()
                for item in os.listdir(temp_repo):
                    if item.startswith(".git"):
                        continue
                    src = os.path.join(temp_repo, item)
                    dst = os.path.join(current_dir, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                self.console.print(
                    f"[green]✅ Successfully pulled from simulator '{sim_name}'"
                )
            return GitResult(success=True, exit_code=0)
        except Exception as e:
            return GitResult(success=False, exit_code=1, error=str(e))

    async def _do_hub_status(
        self, hub_config: dict, command: str, extra_args: List[str]
    ) -> GitResult:
        import subprocess

        try:
            clone_url = (
                self._get_authenticated_url(hub_config)
                or hub_config["repository"]["clone_url"]
            )
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                current_dir = os.getcwd()
                clone_result = subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                )
                if clone_result.returncode != 0:
                    subprocess.run(
                        ["git", "init", "--initial-branch=main", temp_repo],
                        capture_output=True,
                        check=True,
                    )
                    self.console.print(
                        f"📁 Creating isolated view (couldn't fetch remote: {clone_result.stderr.strip()[:50]}...)"
                    )
                else:
                    self.console.print("📡 Comparing against simulator repository")
                os.chdir(temp_repo)
                for item in os.listdir("."):
                    if not item.startswith(".git"):
                        item_path = os.path.join(".", item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                for item in os.listdir(current_dir):
                    if item.startswith(".git") or item == ".plato-hub.json":
                        continue
                    src = os.path.join(current_dir, item)
                    dst = os.path.join(".", item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        shutil.copytree(src, dst)
                git_cmd = ["git", command] + extra_args
                result = subprocess.run(git_cmd, capture_output=False, text=True)
                return GitResult(
                    success=result.returncode == 0, exit_code=result.returncode
                )
        except Exception as e:
            return GitResult(success=False, exit_code=1, error=str(e))

    def link(self, sim_name: str, directory: Optional[str]) -> None:
        async def _link():
            client = Plato()
            try:
                target_dir = directory or os.getcwd()
                self.console.print(f"Looking up simulator '{sim_name}'...")
                simulators = await client.list_gitea_simulators()
                simulator = next(
                    (s for s in simulators if s["name"].lower() == sim_name.lower()),
                    None,
                )
                if not simulator:
                    self.console.print(f"[red]❌ Simulator '{sim_name}' not found.")
                    available = [s["name"] for s in simulators]
                    if available:
                        self.console.print(
                            f"💡 Available simulators: {', '.join(available)}"
                        )
                    return
                if not simulator.get("has_repo", False):
                    self.console.print(
                        f"❌ Simulator '{sim_name}' exists but doesn't have a repository configured.",
                    )
                    self.console.print(
                        "💡 Contact your administrator to set up a repository for this simulator."
                    )
                    return
                repo_info = await client.get_simulator_repository(simulator["id"])
                if not repo_info.get("has_repo", False):
                    self.console.print(
                        f"Repository for simulator '{sim_name}' is not available."
                    )
                    return
                clone_url = repo_info["clone_url"]
                if repo_info.get("admin_credentials") and clone_url.startswith(
                    "https://"
                ):
                    creds = repo_info["admin_credentials"]
                    clone_url = clone_url.replace(
                        "https://", f"https://{creds['username']}:{creds['password']}@"
                    )
                    self.console.print("Using admin credentials for authentication")
                self.console.print(
                    f"Linking directory '{target_dir}' to {repo_info['full_name']}..."
                )
                original_dir = os.getcwd()
                os.chdir(target_dir)
                try:
                    import json

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
                            else repo_info["clone_url"],
                            "description": repo_info.get("description"),
                        },
                        "sync_directory": os.path.basename(target_dir),
                    }
                    config_file = os.path.join(target_dir, ".plato-hub.json")
                    with open(config_file, "w") as f:
                        json.dump(hub_config, f, indent=2)
                    self.console.print(
                        f"[green]✅ Created Plato hub configuration for '{sim_name}'"
                    )
                    self.console.print(
                        f"🔗 Directory '{target_dir}' is now linked to {repo_info['full_name']}"
                    )
                    self.console.print(
                        "💡 This directory will sync with the simulator repo independently"
                    )
                    self.console.print(
                        "💡 Run 'uv run plato hub login' to authenticate"
                    )
                    self.console.print(
                        "💡 Then use 'uv run plato hub git push/pull' to sync"
                    )
                    self.console.print("💡 Your monorepo structure remains intact!")
                finally:
                    os.chdir(original_dir)
            finally:
                await client.close()

        asyncio.run(_link())

    def login(self) -> None:
        async def _login():
            import json
            from datetime import datetime

            client = Plato()
            try:
                self.console.print("🔐 Authenticating with Plato hub...")
                creds = await client.get_gitea_credentials()
                cache_dir = os.path.expanduser("~/.plato-hub")
                os.makedirs(cache_dir, exist_ok=True)
                credentials = {
                    "username": creds["username"],
                    "password": creds["password"],
                    "org_name": creds["org_name"],
                    "cached_at": datetime.now().isoformat(),
                }
                cache_file = os.path.join(cache_dir, "credentials.json")
                with open(cache_file, "w") as f:
                    json.dump(credentials, f, indent=2)
                os.chmod(cache_file, 0o600)
                self._ensure_gitignore_protects_credentials()
                self.console.print("✅ Successfully authenticated with Plato hub")
                self.console.print(f"👤 Username: {creds['username']}")
                self.console.print(f"🏢 Organization: {creds['org_name']}")
                self.console.print("💡 Credentials cached securely for git operations")
            except Exception as e:
                self.console.print(f"[red]❌ Login failed: {e}")
            finally:
                await client.close()

        asyncio.run(_login())

    def repo_info(self, sim_name: str, verbose: bool) -> None:
        async def _repo_info():
            client = Plato()
            try:
                with self.console.status(
                    f"[bold cyan]Looking up simulator '{sim_name}'...",
                    spinner="dots",
                ):
                    simulators = await client.list_gitea_simulators()
                simulator = next(
                    (s for s in simulators if s["name"].lower() == sim_name.lower()),
                    None,
                )
                if not simulator:
                    self.console.print(f"[red]❌ Simulator '{sim_name}' not found.")
                    available = [s["name"] for s in simulators]
                    if available:
                        self.console.print(
                            f"💡 Available simulators: {', '.join(available)}"
                        )
                    return
                self.console.print("\n[bold]DB Link Status[/bold]")
                self.console.print(f"• name: {simulator['name']}")
                self.console.print(f"• id: {simulator['id']}")
                self.console.print(f"• org: {simulator.get('organization_name')}")
                self.console.print(f"• has_repo: {simulator.get('has_repo')}")
                self.console.print(
                    f"• gitea owner/name: {simulator.get('gitea_repo_owner')} / {simulator.get('gitea_repo_name')}"
                )
                with self.console.status(
                    "[bold cyan]Fetching simulator repository details...",
                    spinner="dots",
                ):
                    repo_info = await client.get_simulator_repository(simulator["id"])
                self.console.print("\n[bold]Repository Details (API)[/bold]")
                if repo_info.get("has_repo"):
                    self.console.print(f"• full_name: {repo_info.get('full_name')}")
                    self.console.print(f"• clone_url: {repo_info.get('clone_url')}")
                    self.console.print(f"• ssh_url: {repo_info.get('ssh_url')}")
                    self.console.print(f"• private: {repo_info.get('private')}")
                else:
                    self.console.print("• has_repo: False")
                    self.console.print(f"• message: {repo_info.get('message')}")
                headers = {"X-API-Key": client.api_key}
                my_info = {}
                my_repos = []
                try:
                    async with client.http_session.get(
                        f"{client.base_url}/gitea/my-info", headers=headers
                    ) as r:
                        await client._handle_response_error(r)
                        my_info = await r.json()
                except Exception:
                    pass
                try:
                    async with client.http_session.get(
                        f"{client.base_url}/gitea/my-repositories", headers=headers
                    ) as r:
                        await client._handle_response_error(r)
                        my_repos = await r.json()
                except Exception:
                    pass
                self.console.print("\n[bold]Organization Repositories[/bold]")
                if my_info:
                    self.console.print(
                        f"• org_name: {my_info.get('org_name')} (is_admin={my_info.get('is_admin')})"
                    )
                else:
                    self.console.print("• org_name: unknown (failed to fetch)")
                normalized = sim_name.lower().replace(" ", "-").replace("_", "-")
                candidates = []
                for repo in my_repos or []:
                    name = (repo.get("name") or "").lower()
                    sim_repo_name = (simulator.get("gitea_repo_name") or "").lower()
                    if name in {normalized, sim_repo_name}:
                        candidates.append(repo)
                if candidates:
                    self.console.print("• matching repos found in org:")
                    for repo in candidates:
                        self.console.print(
                            f"  - {repo.get('full_name')} (clone_url={repo.get('clone_url')})"
                        )
                else:
                    self.console.print("• no matching repos found in org")
                if verbose and my_repos:
                    self.console.print("\n[dim]All org repositories:[/dim]")
                    for repo in my_repos:
                        self.console.print(f"  - {repo.get('full_name')}")
                self.console.print("\n[bold]Diagnosis[/bold]")
                if simulator.get("has_repo"):
                    self.console.print("• DB is linked to a repository ✅")
                else:
                    if candidates:
                        self.console.print(
                            "• Repo exists in your org but simulator isn't linked in DB."
                        )
                        self.console.print(
                            "  Suggestion: run 'uv run plato hub clone {sim_name}' to adopt and link."
                        )
                    else:
                        self.console.print(
                            "• No matching repo found under your org. It may be in a different org or named differently."
                        )
                        self.console.print(
                            "  Suggestion: ensure your PLATO_API_KEY belongs to the correct org; then run clone or contact admin."
                        )
            finally:
                await client.close()

        asyncio.run(_repo_info())

    def git(self, args: List[str]) -> None:

        if not args:
            self.console.print("❌ Please provide a git command")
            self.console.print(
                "[yellow]💡 Example: uv run plato hub git status[/yellow]"
            )
            return
        try:
            config_file = ".plato-hub.json"
            hub_config = None
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        hub_config = json.load(f)
                    self.console.print(
                        f"✅ Found Plato hub configuration for '{hub_config['simulator_name']}'",
                    )
                except Exception as e:
                    self.console.print(f"[red]❌ Error reading hub config: {e}")
                    return
            if not hub_config:
                self.console.print(
                    "⚠️  No Plato hub configuration found. Running regular git command..."
                )
                git_cmd = ["git"] + list(args)
                result = subprocess.run(git_cmd, capture_output=False, text=True)
                if result.returncode != 0:
                    raise typer.Exit(result.returncode)
                return
            command = args[0] if args else ""
            if command == "push":
                self._hub_push(hub_config, list(args[1:]) if len(args) > 1 else [])
            elif command == "pull":
                self._hub_pull(hub_config, list(args[1:]) if len(args) > 1 else [])
            elif command in ["status", "log", "diff", "branch"]:
                self._hub_status(
                    hub_config, command, list(args[1:]) if len(args) > 1 else []
                )
            else:
                self.console.print(
                    f"[yellow]⚠️  Running '{command}' in hub-linked directory"
                )
                git_cmd = ["git"] + list(args)
                result = subprocess.run(git_cmd, capture_output=False, text=True)
                if result.returncode != 0:
                    raise typer.Exit(result.returncode)
        except FileNotFoundError:
            self.console.print("❌ Git is not installed or not in PATH")
            raise typer.Exit(1)
        except Exception as e:
            self.console.print(f"[red]❌ Error executing git command: {e}")
            raise typer.Exit(1)

    def _hub_push(self, hub_config: dict, extra_args: List[str]) -> None:
        import subprocess

        try:
            clone_url = self._get_authenticated_url(hub_config)
            if not clone_url:
                self.console.print(
                    "[red]❌ Authentication failed. Run 'uv run plato hub login' first.[/red]"
                )
                return
            sim_name = hub_config["simulator_name"]
            self.console.print(f"📤 Pushing to simulator '{sim_name}'...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                result = subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.console.print(
                        f"❌ Failed to clone simulator repo: {result.stderr.strip()}"
                    )
                    return
                current_dir = os.getcwd()
                for item in os.listdir(current_dir):
                    if item.startswith("."):
                        continue
                    src = os.path.join(current_dir, item)
                    dst = os.path.join(temp_repo, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                os.chdir(temp_repo)
                subprocess.run(["git", "add", "."], check=True)
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"], capture_output=True, text=True
                )
                if not status_result.stdout.strip():
                    self.console.print("[yellow]📝 No changes to push[/yellow]")
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
                push_args = ["git", "push", "origin", "main"] + extra_args
                result = subprocess.run(push_args, capture_output=True, text=True)
                if result.returncode == 0:
                    self.console.print(
                        f"[green]✅ Successfully pushed to simulator '{sim_name}'"
                    )
                else:
                    self.console.print(f"[red]❌ Push failed: {result.stderr.strip()}")
        except Exception as e:
            self.console.print(f"[red]❌ Error during push: {e}")

    def _hub_pull(self, hub_config: dict, extra_args: List[str]) -> None:
        import subprocess

        try:
            clone_url = self._get_authenticated_url(hub_config)
            if not clone_url:
                self.console.print(
                    "[red]❌ Authentication failed. Run 'uv run plato hub login' first.[/red]"
                )
                return
            sim_name = hub_config["simulator_name"]
            self.console.print(f"📥 Pulling from simulator '{sim_name}'...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                result = subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.console.print(
                        f"❌ Failed to clone simulator repo: {result.stderr.strip()}"
                    )
                    return
                current_dir = os.getcwd()
                for item in os.listdir(temp_repo):
                    if item.startswith(".git"):
                        continue
                    src = os.path.join(temp_repo, item)
                    dst = os.path.join(current_dir, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                self.console.print(
                    f"[green]✅ Successfully pulled from simulator '{sim_name}'"
                )
                self.console.print(
                    "💡 Files updated in current directory. Review and commit to your monorepo as needed."
                )
        except Exception as e:
            self.console.print(f"[red]❌ Error during pull: {e}")

    def _hub_status(
        self, hub_config: dict, command: str, extra_args: List[str]
    ) -> None:
        import subprocess

        try:
            clone_url = self._get_authenticated_url(hub_config)
            if not clone_url:
                clone_url = hub_config["repository"]["clone_url"]
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = os.path.join(temp_dir, "temp_repo")
                current_dir = os.getcwd()
                clone_result = subprocess.run(
                    ["git", "clone", clone_url, temp_repo],
                    capture_output=True,
                    text=True,
                )
                if clone_result.returncode != 0:
                    subprocess.run(
                        ["git", "init", "--initial-branch=main", temp_repo],
                        capture_output=True,
                        check=True,
                    )
                    self.console.print(
                        f"📁 Creating isolated view (couldn't fetch remote: {clone_result.stderr.strip()[:50]}...)"
                    )
                else:
                    self.console.print("📡 Comparing against simulator repository")
                os.chdir(temp_repo)
                for item in os.listdir("."):
                    if not item.startswith(".git"):
                        item_path = os.path.join(".", item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                for item in os.listdir(current_dir):
                    if item.startswith(".git") or item == ".plato-hub.json":
                        continue
                    src = os.path.join(current_dir, item)
                    dst = os.path.join(".", item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        shutil.copytree(src, dst)
                git_cmd = ["git", command] + extra_args
                subprocess.run(git_cmd, capture_output=False, text=True)
        except Exception as e:
            self.console.print(f"[red]❌ Error during {command}: {e}")
            # fall through; legacy method returns None
