from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from plato.config import get_config
from plato.models import PlatoTask
from plato.models.task import ScoringType
from plato.exceptions import PlatoClientError
from plato.models.task import EvaluationResult
from plato.sync_env import SyncPlatoEnvironment

import os
import logging
import time
import requests

logger = logging.getLogger(__name__)

config = get_config()


class SyncPlato:
    """Synchronous client for interacting with the Plato API.

    This class provides synchronous methods to create and manage Plato environments, handle API authentication,
    and manage HTTP sessions.

    Attributes:
        api_key (str): The API key used for authentication with Plato API.
        base_url (str): The base URL of the Plato API.
        http_session (Optional[requests.Session]): The requests session for making HTTP requests.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize a new SyncPlato.

        Args:
            api_key (Optional[str]): The API key for authentication. If not provided,
                falls back to the key from config.
        """
        self.api_key = api_key or config.api_key
        self.base_url = base_url or config.base_url
        self._http_session: Optional[requests.Session] = None

    @property
    def http_session(self) -> requests.Session:
        """Get or create a requests client session.

        Returns:
            requests.Session: The active HTTP client session.
        """
        if self._http_session is None:
            self._http_session = requests.Session()
            self._http_session.headers.update({"X-API-Key": self.api_key})
        return self._http_session

    def close(self):
        """Close the requests client session if it exists."""
        if self._http_session is not None:
            self._http_session.close()
            self._http_session = None

    def _handle_response_error(self, response: requests.Response) -> None:
        """Handle HTTP error responses by extracting the actual error message.

        Args:
            response: The requests response object

        Raises:
            PlatoClientError: With the actual error message from the response
        """
        if response.status_code >= 400:
            try:
                # Try to get the error message from the response body
                error_data = response.json()
                error_message = error_data.get('error') or error_data.get('message') or str(error_data)
            except (ValueError, requests.exceptions.JSONDecodeError):
                # Fallback to status text if we can't parse JSON
                error_message = response.reason or f"HTTP {response.status_code}"

            raise PlatoClientError(f"HTTP {response.status_code}: {error_message}")

    def make_environment(
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
    ) -> SyncPlatoEnvironment:
        """Create a new Plato environment for the given task.

        Args:
            env_id (str): The ID of the environment to create.
            open_page_on_start (bool): Whether to open the page on start.
            viewport_width (int): The width of the viewport.
            viewport_height (int): The height of the viewport.
            interface_type (Optional[str]): The type of interface to create. Defaults to "browser".
            record_network_requests (bool): Whether to record network requests.
            record_actions (bool): Whether to record actions.
            env_config (Optional[Dict[str, Any]]): Environment configuration.
            keepalive (bool): If true, jobs will not be killed due to heartbeat failures.
            alias (Optional[str]): Optional alias for the job group.
            fast (bool): Fast mode flag.
            version (Optional[str]): Optional version of the environment.

        Returns:
            SyncPlatoEnvironment: The created environment instance.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(
            f"{self.base_url}/env/make2",
            json={
                "interface_type": interface_type or "noop",
                "interface_width": viewport_width,
                "interface_height": viewport_height,
                "source": "SDK",
                "open_page_on_start": open_page_on_start,
                "env_id": env_id,
                "env_config": env_config or {},
                "record_network_requests": record_network_requests,
                "record_actions": record_actions,
                "keepalive": keepalive,
                "alias": alias,
                "fast": fast,
                "version": version,
                "tag": tag,
                "dataset": dataset,
                "artifact_id": artifact_id,
            },
        )
        self._handle_response_error(response)
        data = response.json()
        return SyncPlatoEnvironment(
            client=self,
            env_id=env_id,
            id=data["job_id"],
            alias=data.get("alias"),
            fast=fast,
        )

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a job.

        Args:
            job_id (str): The ID of the job to check.

        Returns:
            Dict[str, Any]: The job status information.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/env/{job_id}/status")
        self._handle_response_error(response)
        data = response.json()
        logger.debug(f"Job status for job {job_id}: {data}")
        return data

    def get_cdp_url(self, job_id: str) -> str:
        """Get the Chrome DevTools Protocol URL for a job.

        Args:
            job_id (str): The ID of the job to get the CDP URL for.

        Returns:
            str: The CDP URL for the job.

        Raises:
            PlatoClientError: If the API request fails or returns an error.
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/env/{job_id}/cdp_url")
        data = response.json()
        if data["error"] is not None:
            raise PlatoClientError(data["error"])
        return data["data"]["cdp_url"]

    def get_proxy_url(self, job_id: str) -> str:
        """Get the proxy URL for a job.

        Args:
            job_id (str): The ID of the job to get the proxy URL for.

        Returns:
            str: The proxy URL for the job.

        Raises:
            PlatoClientError: If the API request fails or returns an error.
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/env/{job_id}/proxy_url")
        data = response.json()
        if data["error"] is not None:
            raise PlatoClientError(data["error"])
        return data["data"]["proxy_url"]



    def close_environment(self, job_id: str) -> Dict[str, Any]:
        """Close an environment.

        Args:
            job_id (str): The ID of the job to close.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(f"{self.base_url}/env/{job_id}/close")
        self._handle_response_error(response)
        return response.json()

    def backup_environment(self, job_id: str) -> Dict[str, Any]:
        """Create a backup of an environment.

        Args:
            job_id (str): The ID of the job to backup.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(f"{self.base_url}/env/{job_id}/backup")
        self._handle_response_error(response)
        return response.json()

    def reset_environment(
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
            requests.RequestException: If the API request fails.
        """
        body = {
            "test_case_public_id": task.public_id if task else None,
            "agent_version": agent_version,
            "load_browser_state": load_authenticated,
            **kwargs,
        }
        start_time = time.time()
        response = self.http_session.post(
            f"{self.base_url}/env/{job_id}/reset",
            json=body,
        )
        end_time = time.time()
        print(f"Reset time: {end_time - start_time} seconds")
        self._handle_response_error(response)
        return response.json()

    def get_environment_state(self, job_id: str) -> Dict[str, Any]:
        """Get the current state of an environment.

        Args:
            job_id (str): The ID of the job to get state for.

        Returns:
            Dict[str, Any]: The current state of the environment.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/env/{job_id}/state")
        self._handle_response_error(response)
        data = response.json()
        return data["data"]["state"]

    def get_worker_ready(self, job_id: str) -> Dict[str, Any]:
        """Check if the worker for this job is ready and healthy.

        Args:
            job_id (str): The ID of the job to check.

        Returns:
            Dict[str, Any]: The worker ready status information.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/env/{job_id}/worker_ready")
        self._handle_response_error(response)
        return response.json()

    def get_live_view_url(self, job_id: str) -> str:
        """Get the URL for accessing the live view of the environment.

        Args:
            job_id (str): The ID of the job to get the live view URL for.

        Returns:
            str: The URL for accessing the live view of the environment.

        Raises:
            PlatoClientError: If the worker is not ready.
            requests.RequestException: If the API request fails.
        """
        try:
            worker_status = self.get_worker_ready(job_id)
            if not worker_status.get("ready"):
                raise PlatoClientError("Worker is not ready yet")
            root_url = self.base_url.split("/api")[0]
            return os.path.join(root_url, "live", f"{job_id}/")
        except requests.RequestException as e:
            raise PlatoClientError(str(e))

    def send_heartbeat(self, job_id: str) -> Dict[str, Any]:
        """Send a heartbeat to keep the environment active.

        Args:
            job_id (str): The ID of the job to send a heartbeat for.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(f"{self.base_url}/env/{job_id}/heartbeat")
        self._handle_response_error(response)
        return response.json()

    def process_snapshot(self, session_id: str) -> Dict[str, Any]:
        """Process a snapshot of the environment.

        Args:
            session_id (str): The ID of the session to process.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(f"{self.base_url}/snapshot/process/{session_id}")
        self._handle_response_error(response)
        return response.json()

    def evaluate(self, session_id: str, value: Optional[Any] = None, agent_version: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate the environment.

        Args:
            session_id (str): The ID of the session to evaluate.
            value (Optional[Any]): Optional value to include in the evaluation request.
            agent_version (Optional[str]): Optional agent version.

        Returns:
            Dict[str, Any]: The evaluation result.

        Raises:
            requests.RequestException: If the API request fails.
        """
        body = {}
        if value is not None:
            body = {"value": value}

        response = self.http_session.post(
            f"{self.base_url}/env/session/{session_id}/evaluate",
            json=body,
        )
        self._handle_response_error(response)
        res_data = response.json()
        return res_data["score"]

    def post_evaluation_result(
        self,
        session_id: str,
        evaluation_result: EvaluationResult,
        agent_version: Optional[str] = None,
        mutations: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Post an evaluation result to the server.

        Args:
            session_id (str): The ID of the session to post the evaluation result for.
            evaluation_result (EvaluationResult): The evaluation result to post.
            agent_version (Optional[str]): Optional agent version.
            mutations (Optional[List[dict]]): Optional list of mutations.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        body = {
            "success": evaluation_result.success,
            "reason": evaluation_result.reason,
            "agent_version": agent_version,
            "mutations": mutations,
        }
        response = self.http_session.post(
            f"{self.base_url}/env/session/{session_id}/score",
            json=body,
        )
        self._handle_response_error(response)
        return response.json()

    def log(self, session_id: str, log: dict, type: str = "info") -> Dict[str, Any]:
        """Log a message to the server.

        Args:
            session_id (str): The ID of the session to log the message for.
            log (dict): The log to log.
            type (str): The type of log to log.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(
            f"{self.base_url}/env/{session_id}/log",
            json={
                "source": "agent",
                "type": type,
                "message": log,
                "timestamp": datetime.now().isoformat(),
            },
        )
        self._handle_response_error(response)
        return response.json()

    def list_simulators(self) -> List[Dict[str, Any]]:
        """List all environments.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing environments.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/env/simulators")
        self._handle_response_error(response)
        simulators = response.json()
        return [s for s in simulators if s["enabled"]]

    def load_tasks(self, simulator_name: str) -> List[PlatoTask]:
        """Load tasks from a simulator.

        Args:
            simulator_name (str): The name of the simulator to load tasks from. Ex: "espocrm", "doordash"

        Returns:
            List[PlatoTask]: List of tasks from the simulator.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(
            f"{self.base_url}/testcases?simulator_name={simulator_name}&page_size=1000",
        )
        self._handle_response_error(response)
        res = response.json()
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

    def get_active_session(self, job_id: str) -> Dict[str, Any]:
        """Get the active session for a job group.

        Args:
            job_id (str): The ID of the job group to get the active session for.

        Returns:
            Dict[str, Any]: The active session information.

        Raises:
            requests.RequestException: If the API request fails.
            PlatoClientError: If no active session is found.
        """
        response = self.http_session.get(f"{self.base_url}/env/{job_id}/active_session")
        self._handle_response_error(response)
        data = response.json()
        if "error" in data:
            raise PlatoClientError(data["error"])
        return data

    def get_running_sessions_count(self) -> Dict[str, Any]:
        """Get the current number of running sessions for the user's organization.

        Returns:
            Dict[str, Any]: Organization data including organization ID and running sessions count.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/user/organization/running-sessions")
        self._handle_response_error(response)
        return response.json()
