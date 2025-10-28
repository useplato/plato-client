from datetime import datetime
from typing import List, Optional, Dict, Any
from plato.config import get_config
from plato.models import PlatoTask, PlatoTaskMetadata
from plato.models.task import ScoringType
from plato.exceptions import PlatoClientError
from plato.models.task import EvaluationResult
from plato.sync_env import SyncPlatoEnvironment

import os
import logging
import time
import requests

import logfire
from importlib.metadata import version, PackageNotFoundError


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

    @logfire.instrument("SyncPlato.__init__", extract_args=True)
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        feature_flags: Optional[Dict[str, Any]] = None,
        telemetry: bool = False,
    ):
        """Initialize a new SyncPlato.

        Args:
            api_key (Optional[str]): The API key for authentication. If not provided,
                falls back to the key from config.
            base_url (Optional[str]): The base URL for the Plato API. If not provided,
                falls back to the URL from config.
            feature_flags (Optional[Dict[str, Any]]): Feature flags to include in all requests.
        """
        self.api_key = api_key or config.api_key
        self.base_url = base_url or config.base_url
        self.feature_flags = feature_flags or {}
        self._http_session: Optional[requests.Session] = None
        self._telemetry: bool = telemetry
        self._telemetry_headers: Dict[str, str] | None = None
        self._telemetry_configured: bool = False

        # Configure Logfire in noop mode if telemetry is disabled
        if not telemetry:
            self._configure_logfire_noop()

    @property
    @logfire.instrument("SyncPlato.http_session", extract_args=True)
    def http_session(self) -> requests.Session:
        """Get or create a requests client session.

        Returns:
            requests.Session: The active HTTP client session.
        """
        if self._http_session is None:
            self._http_session = requests.Session()
            self._http_session.headers.update({"X-API-Key": self.api_key})
            # Attach feature flags as default cookies for all requests
            if self.feature_flags:
                for name, value in self.feature_flags.items():
                    self._http_session.cookies.set(name, str(value))
            if self._telemetry:
                try:
                    self._init_telemetry()
                except Exception as _e:
                    logger.debug(f"Failed to initialize telemetry: {_e}")
        return self._http_session

    @logfire.instrument("SyncPlato.close", extract_args=True)
    def close(self):
        """Close the requests client session if it exists."""
        if self._http_session is not None:
            self._http_session.close()
            self._http_session = None

    def _init_telemetry(self) -> None:
        if not self._telemetry:
            return

        headers = {"X-API-Key": self.api_key}
        resp = self.http_session.post(
            f"{self.base_url}/telemetry/init", headers=headers
        )
        self._handle_response_error(resp)
        token_data: Dict[str, Any] = resp.json()

        if token_data.get("access_token"):
            token = token_data["access_token"]
            self._telemetry_headers = {"Authorization": f"Bearer {token}"}
            try:
                self._configure_otel_from_token(token_data)
            except Exception as _e:
                logger.debug(f"Failed to initialize OTEL exporter: {_e}")

    def _configure_otel_from_token(self, token_data: Dict[str, Any]) -> None:
        """Configure Logfire with OTLP exporter using token data from server.

        Uses Logfire for instrumentation but sends to our own OTLP endpoint.
        """
        try:
            resource_attrs = token_data.get("resource_attributes", {})

            # Get package version dynamically
            try:
                pkg_version = version("plato-sdk")
            except PackageNotFoundError:
                pkg_version = "unknown"

            # Add standard service attributes
            resource_attrs.update(
                {
                    "service.name": "plato-sdk",
                    "service.version": pkg_version,
                    "telemetry.source": "sdk",
                }
            )

            base_url = token_data.get("otlp_base_url", "").rstrip("/")
            if not base_url:
                raise PlatoClientError(
                    "Telemetry enabled but server did not provide OTLP base URL"
                )

            # Configure logfire to not send to logfire.dev, but to our endpoint
            self._configure_logfire(
                send_to_logfire=False,
                console=False,  # Disable console output
                service_name="plato-sdk",
                service_version=pkg_version,
                trace_sample_rate=1.0,
                # Configure OTLP export
                additional_span_processors=[
                    logfire.integrations.create_otlp_span_processor(
                        endpoint=f"{base_url}/v1/traces",
                        headers=self._telemetry_headers or {},
                        timeout=30,
                    )
                ],
                # Set resource attributes
                resource_attributes=resource_attrs,
            )
        except Exception as e:
            raise PlatoClientError(f"Failed to configure telemetry: {e}")

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
                error_message = (
                    error_data.get("error")
                    or error_data.get("message")
                    or str(error_data)
                )
            except (ValueError, requests.exceptions.JSONDecodeError):
                # Fallback to status text if we can't parse JSON
                error_message = response.reason or f"HTTP {response.status_code}"

            raise PlatoClientError(f"HTTP {response.status_code}: {error_message}")

    @logfire.instrument("SyncPlato.make_environment", extract_args=True)
    def make_environment(
        self,
        env_id: str,
        open_page_on_start: bool = False,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        interface_type: Optional[str] = None,
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

    @logfire.instrument("SyncPlato.get_job_status", extract_args=True)
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

    @logfire.instrument("SyncPlato.get_cdp_url", extract_args=True)
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

    @logfire.instrument("SyncPlato.get_proxy_url", extract_args=True)
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

    @logfire.instrument("SyncPlato.close_environment", extract_args=True)
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

    @logfire.instrument("SyncPlato.backup_environment", extract_args=True)
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

    @logfire.instrument("SyncPlato.reset_environment", extract_args=True)
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

    @logfire.instrument("SyncPlato.get_environment_state", extract_args=True)
    def get_environment_state(
        self, job_id: str, merge_mutations: bool = False
    ) -> Dict[str, Any]:
        """Get the current state of an environment.

        Args:
            job_id (str): The ID of the job to get state for.
            merge_mutations (bool): Whether to merge mutations into the state.

        Returns:
            Dict[str, Any]: The current state of the environment.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(
            f"{self.base_url}/env/{job_id}/state",
            params={"merge_mutations": str(merge_mutations).lower()},
        )
        self._handle_response_error(response)
        data = response.json()
        return data["data"]["state"]

    @logfire.instrument("SyncPlato.get_worker_ready", extract_args=True)
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

    @logfire.instrument("SyncPlato.get_live_view_url", extract_args=True)
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

    @logfire.instrument("SyncPlato.send_heartbeat", extract_args=True)
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

    @logfire.instrument("SyncPlato.process_snapshot", extract_args=True)
    def process_snapshot(self, session_id: str) -> Dict[str, Any]:
        """Process a snapshot of the environment.

        Args:
            session_id (str): The ID of the session to process.

        Returns:
            Dict[str, Any]: The response from the server.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.post(
            f"{self.base_url}/snapshot/process/{session_id}"
        )
        self._handle_response_error(response)
        return response.json()

    @logfire.instrument("SyncPlato.evaluate", extract_args=True)
    def evaluate(
        self,
        session_id: str,
        value: Optional[Any] = None,
        agent_version: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    @logfire.instrument("SyncPlato.post_evaluation_result", extract_args=True)
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

    @logfire.instrument("SyncPlato.log", extract_args=True)
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

    @logfire.instrument("SyncPlato.list_simulators", extract_args=True)
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

    @logfire.instrument("SyncPlato.load_tasks", extract_args=True)
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
                num_validator_human_scores=t.get("defaultScoringConfig", {}).get(
                    "num_sessions_used", 0
                ),
                default_scoring_config=t.get("defaultScoringConfig", {}),
                scoring_type=[ScoringType(st) for st in t.get("scoringTypes", [])]
                if t.get("scoringTypes")
                else None,
                output_schema=t.get("outputSchema"),
                is_sample=t.get("isSample", False),
                simulator_artifact_id=t.get("simulatorArtifactId"),
                metadata=PlatoTaskMetadata(
                    reasoning_level=t.get("metadataConfig", {}).get("reasoningLevel"),
                    skills=t.get("metadataConfig", {}).get("skills", []),
                    capabilities=t.get("metadataConfig", {}).get("capabilities", []),
                    tags=t.get("metadataConfig", {}).get("tags", []),
                    rejected=t.get("metadataConfig", {}).get("rejected", False),
                )
                if t.get("metadataConfig")
                else None,
            )
            for t in test_cases
        ]

    @logfire.instrument("SyncPlato.get_active_session", extract_args=True)
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

    @logfire.instrument("SyncPlato.get_running_sessions_count", extract_args=True)
    def get_running_sessions_count(self) -> Dict[str, Any]:
        """Get the current number of running sessions for the user's organization.

        Returns:
            Dict[str, Any]: Organization data including organization ID and running sessions count.

        Raises:
            requests.RequestException: If the API request fails.
        """
        response = self.http_session.get(
            f"{self.base_url}/user/organization/running-sessions"
        )
        self._handle_response_error(response)
        return response.json()

    def _configure_logfire_noop(self) -> None:
        """Configure Logfire in no-op mode to avoid any logging overhead."""
        if not self._telemetry_configured:
            try:
                logfire.configure(send_to_logfire=False, console=False)
                self._telemetry_configured = True
            except Exception as e:
                logger.debug(f"Failed to configure Logfire in noop mode: {e}")

    def _configure_logfire(self, **kwargs) -> None:
        """Configure Logfire with the given parameters, ensuring it's only done once."""
        if not self._telemetry_configured:
            try:
                logfire.configure(**kwargs)
                self._telemetry_configured = True
            except Exception as e:
                logger.debug(f"Failed to configure Logfire: {e}")
                # Fall back to noop mode
                self._configure_logfire_noop()
