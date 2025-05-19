from datetime import datetime
from typing import List, Optional, Dict, Any
from plato.config import get_config
from plato.models import PlatoTask, PlatoEnvironment
from plato.exceptions import PlatoClientError
from plato.models.task import EvaluationResult

import aiohttp
import os
import logging
import time

logger = logging.getLogger(__name__)

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
            # Set comprehensive timeout settings:
            # - total: overall operation timeout (10 mins)
            # - connect: timeout for connection (60s)
            # - sock_read: timeout for reading data (10 mins)
            # - sock_connect: timeout for connecting to peer (60s)
            timeout = aiohttp.ClientTimeout(
                total=600,  # 10 minutes
                connect=60,
                sock_read=600,  # 10 minutes
                sock_connect=60,
            )
            self._http_session = aiohttp.ClientSession(timeout=timeout)
        return self._http_session

    async def close(self):
        """Close the aiohttp client session if it exists."""
        if self._http_session is not None and not self._http_session.closed:
            await self._http_session.close()
            self._http_session = None

    async def make_environment(
        self,
        env_id: str,
        open_page_on_start: bool = False,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
    ) -> PlatoEnvironment:
        """Create a new Plato environment for the given task.

        Args:
            env_id (str): The ID of the environment to create.
            open_page_on_start (bool): Whether to open the page on start.
            viewport_width (int): The width of the viewport.
            viewport_height (int): The height of the viewport.

        Returns:
            PlatoEnvironment: The created environment instance.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/make2",
            json={
                "interface_type": "browser",
                "interface_width": viewport_width,
                "interface_height": viewport_height,
                "source": "SDK",
                "open_page_on_start": open_page_on_start,
                "env_id": env_id,
                "env_config": {},
            },
            headers=headers,
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return PlatoEnvironment(client=self, id=data["job_id"], sim_job_id=data.get("sim_job_id"))

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
            f"{self.base_url}/env/{job_id}/status", headers=headers
        ) as response:
            response.raise_for_status()
            response = await response.json()
            logger.debug(f"Job status for job {job_id}: {response}")
            return response

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
            f"{self.base_url}/env/{job_id}/cdp_url", headers=headers
        ) as response:
            data = await response.json()
            if data["error"] is not None:
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
            f"{self.base_url}/env/{job_id}/close", headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def reset_environment(
        self,
        job_id: str,
        task: Optional[PlatoTask] = None,
        agent_version: Optional[str] = None,
    ) -> Dict[str, Any]:
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
        body = {
            "test_case_public_id": task.public_id if task else None,
            "agent_version": agent_version,
        }
        start_time = time.time()
        async with self.http_session.post(
            f"{self.base_url}/env/{job_id}/reset", headers=headers, json=body
        ) as response:
            end_time = time.time()
            print(f"Reset time: {end_time - start_time} seconds")
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
            f"{self.base_url}/env/{job_id}/state", headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data["data"]["state"]

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
            f"{self.base_url}/env/{job_id}/worker_ready", headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_live_view_url(self, job_id: str) -> str:
        """Get the URL for accessing the live view of the environment.

        Args:
            job_id (str): The ID of the job to get the live view URL for.

        Returns:
            str: The URL for accessing the live view of the environment.

        Raises:
            PlatoClientError: If the worker is not ready.
            aiohttp.ClientError: If the API request fails.
        """
        try:
            worker_status = await self.get_worker_ready(job_id)
            if not worker_status.get("ready"):
                raise PlatoClientError("Worker is not ready yet")
            root_url = self.base_url.split("/api")[0]
            return os.path.join(root_url, "live", f"{job_id}/")
        except aiohttp.ClientError as e:
            raise PlatoClientError(str(e))

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
            f"{self.base_url}/env/{job_id}/heartbeat", headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def process_snapshot(self, session_id: str) -> Dict[str, Any]:
        """Process a snapshot of the environment.

        Args:
            session_id (str): The ID of the session to process.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/snapshot/process/{session_id}",
            headers=headers,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def evaluate(
        self, session_id: str, agent_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate the environment.

        Args:
            session_id (str): The ID of the session to evaluate.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/session/{session_id}/evaluate",
            headers=headers,
        ) as response:
            response.raise_for_status()
            res_data = await response.json()
            return res_data["score"]

    async def post_evaluation_result(
        self,
        session_id: str,
        evaluation_result: EvaluationResult,
        agent_version: Optional[str] = None,
        mutations: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Post an evaluation result to the server.

        Args:
            job_id (str): The ID of the job to post the evaluation result for.
            evaluation_result (EvaluationResult): The evaluation result to post.
        """
        body = {
            "success": evaluation_result.success,
            "reason": evaluation_result.reason,
            "agent_version": agent_version,
            "mutations": mutations,
        }
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/session/{session_id}/score",
            headers=headers,
            json=body,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def log(
        self, session_id: str, log: dict, type: str = "info"
    ) -> Dict[str, Any]:
        """Log a message to the server.

        Args:
            session_id (str): The ID of the session to log the message for.
            log (dict): The log to log.
            type (str): The type of log to log.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/{session_id}/log",
            headers=headers,
            json={
                "source": "agent",
                "type": type,
                "message": log,
                "timestamp": datetime.now().isoformat(),
            },
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def list_simulators(self) -> List[Dict[str, Any]]:
        """List all environments.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing environments.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/env/simulators", headers=headers
        ) as response:
            response.raise_for_status()
            simulators = await response.json()
            return [s for s in simulators if s["enabled"]]

    async def load_tasks(self, simulator_name: str) -> List[PlatoTask]:
        """Load tasks from a simulator.

        Args:
            simulator_name (str): The name of the simulator to load tasks from. Ex: "espocrm", "doordash"
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/testcases?simulator_name={simulator_name}&page_size=1000",
            headers=headers,
        ) as response:
            response.raise_for_status()
            res = await response.json()
            test_cases = res["testcases"]
            return [
                PlatoTask(
                    public_id=t["publicId"],
                    name=t["name"],
                    prompt=t["prompt"],
                    start_url=t["startUrl"],
                    env_id=t["simulator"]["name"],
                )
                for t in test_cases
            ]

    async def list_simulator_tasks_by_id(
        self, simulator_id: str
    ) -> List[Dict[str, Any]]:
        """Get all tasks associated with an environment.

        Args:
            simulator_id (str): The ID of the simulator to get tasks for.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing tasks and pagination information.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/testcases?simulator_id={simulator_id}&page_size=1000",
            headers=headers,
        ) as response:
            response.raise_for_status()
            res = await response.json()
            return res["testcases"]
