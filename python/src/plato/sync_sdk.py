from datetime import datetime
from typing import List, Optional, Dict, Any
from plato.config import get_config
from plato.models import PlatoTask
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

    def make_environment(
        self,
        env_id: str,
        open_page_on_start: bool = False,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
    ) -> SyncPlatoEnvironment:
        """Create a new Plato environment for the given task.

        Args:
            env_id (str): The ID of the environment to create.
            open_page_on_start (bool): Whether to open the page on start.
            viewport_width (int): The width of the viewport.
            viewport_height (int): The height of the viewport.

        Returns:
            SyncPlatoEnvironment: The created environment instance.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(
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
        )
        response.raise_for_status()
        data = response.json()
        return SyncPlatoEnvironment(client=self, id=data["job_id"], sim_job_id=data.get("sim_job_id"))

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
        response.raise_for_status()
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
        response.raise_for_status()
        return response.json()

    def reset_environment(
        self,
        job_id: str,
        task: Optional[PlatoTask] = None,
        agent_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reset an environment with an optional new task.

        Args:
            job_id (str): The ID of the job to reset.
            task (Optional[PlatoTask]): Optional new task for the environment.
            agent_version (Optional[str]): Optional agent version.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        body = {
            "test_case_public_id": task.public_id if task else None,
            "agent_version": agent_version,
        }
        start_time = time.time()
        response = self.http_session.post(
            f"{self.base_url}/env/{job_id}/reset",
            json=body,
        )
        end_time = time.time()
        print(f"Reset time: {end_time - start_time} seconds")
        response.raise_for_status()
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
        response.raise_for_status()
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
        response.raise_for_status()
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
        response.raise_for_status()
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
        response.raise_for_status()
        return response.json()

    def evaluate(self, session_id: str, agent_version: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate the environment.

        Args:
            session_id (str): The ID of the session to evaluate.
            agent_version (Optional[str]): Optional agent version.

        Returns:
            Dict[str, Any]: The evaluation result.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(
            f"{self.base_url}/env/session/{session_id}/evaluate",
        )
        response.raise_for_status()
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
        response.raise_for_status()
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
        response.raise_for_status()
        return response.json()

    def list_simulators(self) -> List[Dict[str, Any]]:
        """List all environments.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing environments.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(f"{self.base_url}/env/simulators")
        response.raise_for_status()
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
        response.raise_for_status()
        res = response.json()
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