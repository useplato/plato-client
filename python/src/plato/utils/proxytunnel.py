import logging
import os
import platform
import shutil
import subprocess
from typing import Optional


logger = logging.getLogger(__name__)


def is_command_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def find_proxytunnel_path() -> Optional[str]:
    path = shutil.which("proxytunnel")
    if path:
        return path
    # Common install locations
    for candidate in (
        "/opt/homebrew/bin/proxytunnel",
        "/usr/local/bin/proxytunnel",
        "/usr/bin/proxytunnel",
        "/bin/proxytunnel",
    ):
        if os.path.exists(candidate):
            return candidate
    return None


def install_proxytunnel_noninteractive() -> bool:
    """Attempt to install proxytunnel using the platform's package manager.

    Returns True on success, False otherwise. Avoids interactive prompts.
    """
    try:
        if is_command_available("proxytunnel"):
            logger.info("proxytunnel is already installed")
            return True

        system = platform.system().lower()

        if system == "darwin":
            # macOS: prefer Homebrew
            if is_command_available("brew"):
                env = os.environ.copy()
                env["NONINTERACTIVE"] = "1"
                # Try list first to skip reinstall
                list_res = subprocess.run(
                    ["brew", "list", "proxytunnel"], capture_output=True, text=True
                )
                if list_res.returncode != 0:
                    res = subprocess.run(
                        ["brew", "install", "proxytunnel"],
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    if res.returncode != 0:
                        logger.error("Homebrew install failed: %s", res.stderr.strip())
                        return False
            else:
                logger.warning(
                    "Homebrew not found. Install Homebrew or install proxytunnel manually."
                )
                return False

        elif system == "linux":
            # Try common package managers, preferring non-interactive with sudo -n
            if is_command_available("apt-get"):
                cmd = [
                    "sudo",
                    "-n",
                    "bash",
                    "-lc",
                    "apt-get update && apt-get install -y proxytunnel",
                ]
            elif is_command_available("dnf"):
                cmd = ["sudo", "-n", "dnf", "install", "-y", "proxytunnel"]
            elif is_command_available("yum"):
                cmd = ["sudo", "-n", "yum", "install", "-y", "proxytunnel"]
            elif is_command_available("pacman"):
                cmd = ["sudo", "-n", "pacman", "-Sy", "--noconfirm", "proxytunnel"]
            elif is_command_available("apk"):
                cmd = ["sudo", "-n", "apk", "add", "--no-cache", "proxytunnel"]
            else:
                logger.warning(
                    "Unsupported Linux distro: please install 'proxytunnel' via your package manager."
                )
                return False

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                hint = " (tip: re-run with sudo)" if "sudo" in cmd[0:1] else ""
                logger.error(
                    "proxytunnel installation failed%s: %s",
                    hint,
                    res.stderr.strip() or res.stdout.strip(),
                )
                return False

        else:
            logger.warning(
                "Unsupported platform '%s'. Install proxytunnel manually.", system
            )
            return False

        # Verify installation
        if not is_command_available("proxytunnel"):
            logger.error("proxytunnel not found in PATH after installation")
            return False

        # Quick sanity check
        check = subprocess.run(["proxytunnel", "-h"], capture_output=True, text=True)
        if check.returncode not in (0, 1):  # -h may exit 1 depending on build
            logger.warning(
                "proxytunnel installed but health check returned %s", check.returncode
            )
        logger.info("proxytunnel installed successfully")
        return True
    except Exception as e:
        logger.error("Failed to install proxytunnel: %s", e)
        return False
