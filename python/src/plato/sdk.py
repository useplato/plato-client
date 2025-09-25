from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from plato.config import get_config
from plato.models import PlatoTask, PlatoEnvironment
from plato.models.task import ScoringType
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

    async def _handle_response_error(self, response: aiohttp.ClientResponse) -> None:
        """Handle HTTP error responses by extracting the actual error message.

        Args:
            response: The aiohttp response object

        Raises:
            PlatoClientError: With the actual error message from the response
        """
        if response.status >= 400:
            try:
                # Try to get the error message from the response body
                error_data = await response.json()
                error_message = error_data.get('error') or error_data.get('message') or str(error_data)
            except (aiohttp.ContentTypeError, ValueError):
                # Fallback to status text if we can't parse JSON
                error_message = response.reason or f"HTTP {response.status}"

            raise PlatoClientError(f"HTTP {response.status}: {error_message}")

    async def make_environment(
        self,
        env_id: str,
        open_page_on_start: bool = False,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        interface_type: Optional[Literal["browser"]] = "browser",
        record_network_requests: bool = False,
        record_actions: bool = False,
        env_config: Optional[Dict[str, Any]] = None,
        keepalive: bool = False,
        alias: Optional[str] = None,
        fast: bool = False,
        version: Optional[str] = None,
        tag: Optional[str] = None,
        dataset: Optional[str] = None,
        artifact_id: Optional[str] = None,
    ) -> PlatoEnvironment:
        """Create a new Plato environment for the given task.

        Args:
            env_id (str): The ID of the environment to create.
            open_page_on_start (bool): Whether to open the page on start.
            viewport_width (int): The width of the viewport.
            viewport_height (int): The height of the viewport.
            interface_type (Optional[str]): The type of interface to create. Defaults to None.
            record_network_requests (bool): Whether to record network requests.
            record_actions (bool): Whether to record actions.
            env_config (Optional[Dict[str, Any]]): Environment configuration.
            keepalive (bool): If true, jobs will not be killed due to heartbeat failures.
            alias (Optional[str]): Optional alias for the job group.
            fast (bool): Fast mode flag.
            version (Optional[str]): Optional version of the environment.

        Returns:
            PlatoEnvironment: The created environment instance.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/make2",
            json={
                "interface_type": interface_type or "noop",
                "interface_width": viewport_width,
                "interface_height": viewport_height,
                "source": "SDK",
                "open_page_on_start": open_page_on_start,
                "env_id": env_id,
                "tag": tag,
                "dataset": dataset,
                "artifact_id": artifact_id,
                "env_config": env_config or {},
                "record_network_requests": record_network_requests,
                "record_actions": record_actions,
                "keepalive": keepalive,
                "alias": alias,
                "fast": fast,
                "version": version,
            },
            headers=headers,
        ) as response:
            await self._handle_response_error(response)
            data = await response.json()
            return PlatoEnvironment(
                client=self,
                env_id=env_id,
                id=data["job_id"],
                alias=data.get("alias"),
                fast=fast,
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
            f"{self.base_url}/env/{job_id}/status", headers=headers
        ) as response:
            await self._handle_response_error(response)
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

    async def get_proxy_url(self, job_id: str) -> str:
        """Get the proxy URL for a job.

        Args:
            job_id (str): The ID of the job to get the proxy URL for.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/env/{job_id}/proxy_url", headers=headers
        ) as response:
            data = await response.json()
            if data["error"] is not None:
                raise PlatoClientError(data["error"])
            return data["data"]["proxy_url"]

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
            await self._handle_response_error(response)
            return await response.json()

    async def backup_environment(self, job_id: str) -> Dict[str, Any]:
        """Create a backup of an environment.

        Args:
            job_id (str): The ID of the job to backup.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/env/{job_id}/backup", headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

    async def reset_environment(
        self,
        job_id: str,
        task: Optional[PlatoTask] = None,
        agent_version: Optional[str] = None,
        load_authenticated: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Reset an environment with an optional new task.

        Args:
            job_id (str): The ID of the job to reset.
            task (Optional[PlatoTask]): Optional new task for the environment.
            agent_version (Optional[str]): Optional agent version.
            load_authenticated (bool): Whether to load authenticated browser state.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        body = {
            "test_case_public_id": task.public_id if task else None,
            "agent_version": agent_version,
            "load_browser_state": load_authenticated,
            **kwargs,
        }
        start_time = time.time()
        async with self.http_session.post(
            f"{self.base_url}/env/{job_id}/reset", headers=headers, json=body
        ) as response:
            end_time = time.time()
            print(f"Reset time: {end_time - start_time} seconds")
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
            return await response.json()

    async def evaluate(
        self, session_id: str, value: Optional[Any] = None, agent_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate the environment.

        Args:
            session_id (str): The ID of the session to evaluate.
            value (Optional[Any]): Optional value to include in the evaluation request.
            agent_version (Optional[str]): Optional agent version.
        """
        headers = {"X-API-Key": self.api_key}
        body = {}
        if value is not None:
            body = {"value": value}

        async with self.http_session.post(
            f"{self.base_url}/env/session/{session_id}/evaluate",
            headers=headers,
            json=body,
        ) as response:
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
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
            await self._handle_response_error(response)
            res = await response.json()
            test_cases = res["testcases"]
            return [
                PlatoTask(
                    public_id=t["publicId"],
                    name=t["name"],
                    prompt=t["prompt"],
                    start_url=t["startUrl"],
                    env_id=t["simulator"]["name"],
                    average_time=t.get("averageTimeTaken"),
                    average_steps=t.get("averageStepsTaken"),
                    num_validator_human_scores=t.get("defaultScoringConfig", {}).get("num_sessions_used", 0),
                    default_scoring_config=t.get("defaultScoringConfig", {}),
                    scoring_type=[ScoringType(st) for st in t.get("scoringTypes", [])] if t.get("scoringTypes") else None,
                    output_schema=t.get("outputSchema"),
                    is_sample=t.get("isSample", False),
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
            await self._handle_response_error(response)
            res = await response.json()
            return res["testcases"]

    async def get_active_session(self, job_id: str) -> Dict[str, Any]:
        """Get the active session for a job group.

        Args:
            job_id (str): The ID of the job group to get the active session for.

        Returns:
            Dict[str, Any]: The active session information.

        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If no active session is found.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/env/{job_id}/active_session", headers=headers
        ) as response:
            await self._handle_response_error(response)
            data = await response.json()
            if "error" in data:
                raise PlatoClientError(data["error"])
            return data

    async def get_running_sessions_count(self) -> Dict[str, Any]:
        """Get the current number of running sessions for the user's organization.

        Returns:
            Dict[str, Any]: Organization data including organization ID and running sessions count.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/user/organization/running-sessions", headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

    # Gitea-related methods for hub commands

    async def get_gitea_info(self) -> Dict[str, Any]:
        """Get the current user's Gitea info (auto-provisions if needed).

        Returns:
            Dict[str, Any]: User's Gitea information including username and org_name.

        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If user doesn't have admin access.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/gitea/my-info", headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

    async def list_gitea_simulators(self) -> List[Dict[str, Any]]:
        """Get simulators that user has access to view repos for.

        Returns:
            List[Dict[str, Any]]: List of simulators with repository info.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/gitea/simulators", headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

    async def get_simulator_repository(self, simulator_id: int) -> Dict[str, Any]:
        """Get repository details for a specific simulator.

        Args:
            simulator_id (int): The ID of the simulator to get repository info for.

        Returns:
            Dict[str, Any]: Repository information for the simulator.

        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If simulator not found or access denied.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/gitea/simulators/{simulator_id}/repo", headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

    async def get_gitea_credentials(self) -> Dict[str, Any]:
        """Get Gitea admin credentials for the organization.

        Returns:
            Dict[str, Any]: Gitea credentials including username and password.

        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If user doesn't have access.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/gitea/credentials", headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

    async def create_simulator(self, name: str, description: str = None, sim_type: str = "docker_app") -> Dict[str, Any]:
        """Create a new simulator.

        Args:
            name (str): The name of the simulator
            description (str, optional): Description of the simulator
            sim_type (str, optional): Type of simulator (default: docker_app)

        Returns:
            Dict[str, Any]: Created simulator information.

        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If creation fails.
        """
        headers = {"X-API-Key": self.api_key}

        # Basic simulator configuration
        simulator_data = {
            "name": name,
            "description": description or f"Simulator for {name}",
            "simType": sim_type,
            "enabled": True,
            "config": {
                "image_name": f"plato-{name}:latest",
                "internal_app_port": 80,
                "supported_providers": ["ecs_service", "ecs_task"]
            }
        }

        async with self.http_session.post(
            f"{self.base_url}/env/simulators",
            json=simulator_data,
            headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

    async def create_simulator_repository(self, simulator_id: int) -> Dict[str, Any]:
        """Create a repository for a simulator.

        Args:
            simulator_id (int): The ID of the simulator to create repository for.

        Returns:
            Dict[str, Any]: Created repository information.

        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If creation fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.post(
            f"{self.base_url}/gitea/simulators/{simulator_id}/repo",
            headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

