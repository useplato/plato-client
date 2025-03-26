from typing import Optional, Dict, Any
import aiohttp
from plato.config import get_config
from plato.models import PlatoTask, PlatoEnvironment
from plato.exceptions import PlatoClientError

config = get_config()

class Plato:
    """Client for interacting with the Plato API.

    This class provides methods to create and manage Plato environments, handle API authentication,
    and manage HTTP sessions.

    Attributes:
        api_key (str): The API key used for authentication with Plato API.
        base_url (str): The base URL of the Plato API.
        http_session (Optional[aiohttp.ClientSession]): The aiohttp session for making HTTP requests.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize a new Plato.

        Args:
            api_key (Optional[str]): The API key for authentication. If not provided,
                falls back to the key from config.
        """
        self.api_key = api_key or config.api_key
        self.base_url = base_url or config.base_url
        self._http_session: Optional[aiohttp.ClientSession] = None

    @property
    def http_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp client session.

        Returns:
            aiohttp.ClientSession: The active HTTP client session.
        """
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def close(self):
        """Close the aiohttp client session if it exists."""
        if self._http_session is not None and not self._http_session.closed:
            await self._http_session.close()
            self._http_session = None

    async def make_environment(self, env_id: str) -> PlatoEnvironment:
        """Create a new Plato environment for the given task.

        Args:
            task (PlatoTask): The task to create an environment for.

        Returns:
            PlatoEnvironment: The created environment instance.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/make",
            json={
                "config": {
                    "type": "browser",
                    "browser_config": {
                        "type": "playwright",
                        "cdp_port": 9222,
                        "headless": False,
                        "viewport_size": [1920, 1080]
                    },
                    "simulator_config": {
                        "type": "proxy",
                        "env_id": env_id,
                        "num_workers": 4,
                        "proxy_config": {
                            "host": "localhost",
                            "port": 8000,
                        }
                    },
                    "recording_config": {
                        "record_rrweb": True,
                        "record_network_requests": True
                    }
                }
            },
            headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return PlatoEnvironment(
                client=self,
                id=data["job_id"]
            )

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a job.

        Args:
            job_id (str): The ID of the job to check.

        Returns:
            Dict[str, Any]: The job status information.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/env/{job_id}/status",
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_cdp_url(self, job_id: str) -> str:
        """Get the Chrome DevTools Protocol URL for a job.

        Args:
            job_id (str): The ID of the job to get the CDP URL for.

        Returns:
            str: The CDP URL for the job.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/env/{job_id}/cdp_url",
            headers=headers
        ) as response:
            data = await response.json()
            if data['error'] is not None:
                raise PlatoClientError(data["error"])
            return data["data"]["cdp_url"]

    async def close_environment(self, job_id: str) -> Dict[str, Any]:
        """Close an environment.

        Args:
            job_id (str): The ID of the job to close.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/{job_id}/close",
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def reset_environment(self, job_id: str, task: Optional[PlatoTask] = None) -> Dict[str, Any]:
        """Reset an environment with an optional new task.

        Args:
            job_id (str): The ID of the job to reset.
            task (Optional[PlatoTask]): Optional new task for the environment.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        params = {"task": task.dict() if task else None}
        async with self.http_session.post(
            f"{self.base_url}/env/{job_id}/reset",
            headers=headers,
            json=params
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_environment_state(self, job_id: str) -> Dict[str, Any]:
        """Get the current state of an environment.

        Args:
            job_id (str): The ID of the job to get state for.

        Returns:
            Dict[str, Any]: The current state of the environment.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/env/{job_id}/state",
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_worker_ready(self, job_id: str) -> Dict[str, Any]:
        """Check if the worker for this job is ready and healthy.

        Args:
            job_id (str): The ID of the job to check.

        Returns:
            Dict[str, Any]: The worker ready status information including:
                - ready (bool): Whether the worker is ready
                - worker_ip (Optional[str]): The worker's IP if ready
                - worker_port (Optional[int]): The worker's port if ready
                - health_status (Optional[Dict]): The worker's health status if ready
                - error (Optional[str]): Error message if not ready

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/env/{job_id}/worker_ready",
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_live_view_url(self, job_id: str) -> str:
        """Get the URL for accessing the live view of the environment.

        The live view provides a browser-based view of the environment through noVNC.

        Args:
            job_id (str): The ID of the job to get the live view URL for.

        Returns:
            str: The URL for accessing the live view of the environment.

        Raises:
            PlatoClientError: If the worker is not ready or lacks a public IP.
            aiohttp.ClientError: If the API request fails.
        """
        worker_status = await self.get_worker_ready(job_id)
        
        if not worker_status.get("ready", False):
            raise PlatoClientError("Worker is not ready yet")
            
        worker_public_ip = worker_status.get("worker_public_ip")
        if not worker_public_ip:
            raise PlatoClientError("Worker public IP not available")
            
        return f"http://{worker_public_ip}:6080"
        
    async def send_heartbeat(self, job_id: str) -> Dict[str, Any]:
        """Send a heartbeat to keep the environment active.
        
        The environment requires regular heartbeats to stay active. Without
        heartbeats, inactive environments may be terminated.
        
        Args:
            job_id (str): The ID of the job to send a heartbeat for.
            
        Returns:
            Dict[str, Any]: The response from the server.
            
        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/{job_id}/heartbeat",
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()
