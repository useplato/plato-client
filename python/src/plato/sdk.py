from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from plato.config import get_config
from plato.models import PlatoTask, PlatoEnvironment
from plato.exceptions import PlatoClientError
from plato.models.task import EvaluationResult

import aiohttp
import os
import logging
import time
import json
import asyncio
import yaml

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

    async def _listen_for_sse_result(
        self,
        correlation_id: str,
        timeout: int = 600
    ) -> Dict[str, Any]:
        """Listen for SSE results for a given correlation ID.
        
        Args:
            correlation_id (str): The correlation ID to listen for
            timeout (int): Timeout in seconds
            
        Returns:
            Dict[str, Any]: The final result from the SSE stream
            
        Raises:
            PlatoClientError: If the operation fails or times out
        """
        headers = {"X-API-Key": self.api_key}
        sse_url = f"{self.base_url}/public-build/events/{correlation_id}"
        
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                logger.info(f"Connecting to SSE stream: {sse_url}")
                async with session.get(sse_url, headers=headers) as response:
                    await self._handle_response_error(response)
                    logger.info(f"SSE connection established, response status: {response.status}")
                    
                    buffer = ""
                    try:
                        async for chunk in response.content:
                            chunk_str = chunk.decode('utf-8')
                            # Handle escaped newlines that come from the SSE stream
                            chunk_str = chunk_str.replace('\\n', '\n')
                            buffer += chunk_str
                            # Process complete lines
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                
                                if not line:
                                    continue
                                    
                                if line.startswith('data: '):
                                    try:
                                        data_str = line[6:]  # Remove 'data: ' prefix
                                        event_data = json.loads(data_str)
                                        
                                        # Check for completion events
                                        event_type = event_data.get('event_type')
                                        
                                        if event_type == 'connected':
                                            logger.info(f"Connected to SSE stream for {correlation_id}")
                                            continue
                                        
                                        elif event_type == 'completed':
                                            logger.info(f"Operation {correlation_id} completed successfully")
                                            return {
                                                'success': True,
                                                'data': event_data,
                                                'message': event_data.get('message', 'Operation completed successfully')
                                            }
                                        
                                        elif event_type == 'failed':
                                            error_msg = event_data.get('error') or event_data.get('message', 'Operation failed')
                                            logger.error(f"Operation {correlation_id} failed: {error_msg}")
                                            raise PlatoClientError(f"Operation failed: {error_msg}")
                                        
                                        else:
                                            logger.info(f"Received event {event_type} for {correlation_id}: {event_data}")
                                            
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Failed to parse SSE data: {data_str}. Error: {e}")
                                        continue
                                
                                elif line.startswith('event: '):
                                    # Event type line, can be used for additional processing if needed
                                    continue
                    
                    except aiohttp.ClientPayloadError as e:
                        logger.warning(f"SSE stream ended or connection lost: {e}")
                        # Stream ended - check if we received any final events in the buffer
                        if buffer.strip():
                            # Process any remaining lines in buffer
                            remaining_lines = buffer.strip().split('\n')
                            for line in remaining_lines:
                                line = line.strip()
                                if line.startswith('data: '):
                                    try:
                                        data_str = line[6:]
                                        event_data = json.loads(data_str)
                                        event_type = event_data.get('event_type')
                                        
                                        if event_type == 'completed':
                                            logger.info(f"Operation {correlation_id} completed successfully")
                                            return {
                                                'success': True,
                                                'data': event_data,
                                                'message': event_data.get('message', 'Operation completed successfully')
                                            }
                                        elif event_type == 'failed':
                                            error_msg = event_data.get('error') or event_data.get('message', 'Operation failed')
                                            raise PlatoClientError(f"Operation failed: {error_msg}")
                                    except json.JSONDecodeError:
                                        continue
                        
        except asyncio.TimeoutError:
            raise PlatoClientError(f"Operation {correlation_id} timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Exception in SSE listener: {e}")
            raise PlatoClientError(f"Failed to listen for SSE results: {str(e)}")
        
        # If we get here, the stream ended without a completion event
        raise PlatoClientError(f"SSE stream ended unexpectedly for operation {correlation_id}")

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

    # VM Builder API Methods
    
    async def create_vm(
        self,
        service_name: str,
        version: str = "latest",
        alias: Optional[str] = None,
        vcpu_count: int = 1,
        mem_size_mib: int = 2048,
        overlay_size_mb: int = 8192,
        port: int = 8080,
        wait_time: int = 30,
        vm_timeout: int = 1800,
        messaging_port: int = 7000
    ) -> Dict[str, Any]:
        """Create a new VM.
        
        Args:
            service_name (str): Name of the service to create VM for
            version (str): Version of the service
            alias (Optional[str]): Optional alias for the VM
            vcpu_count (int): Number of vCPUs
            mem_size_mib (int): Memory size in MiB
            overlay_size_mb (int): Overlay size in MB (max 8192)
            port (int): Service port (min 1024)
            wait_time (int): Wait time in seconds
            vm_timeout (int): VM timeout in seconds (max 1800)
            messaging_port (int): Messaging port
            
        Returns:
            Dict[str, Any]: VM creation response
            
        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        
        request_data = {
            "service": service_name,
            "version": version,
            "alias": alias,
            "vcpu_count": vcpu_count,
            "mem_size_mib": mem_size_mib,
            "overlay_size_mb": overlay_size_mb,
            "port": port,
            "wait_time": wait_time,
            "vm_timeout": vm_timeout,
            "messaging_port": messaging_port
        }
        
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/create",
            json=request_data,
            headers=headers,
        ) as response:
            await self._handle_response_error(response)
            initial_response = await response.json()
            
            # Wait for SSE completion
            correlation_id = initial_response.get("correlation_id")
            if correlation_id:
                logger.info(f"Waiting for VM creation to complete (correlation_id: {correlation_id})")
                sse_result = await self._listen_for_sse_result(correlation_id, vm_timeout)
                
                # Update the response with actual status
                if sse_result.get('success'):
                    initial_response["status"] = "running"
                    if "data" in sse_result and "ssh_ip" in sse_result["data"]:
                        initial_response["ssh_ip"] = sse_result["data"]["ssh_ip"]
                    if "data" in sse_result and "host_ip" in sse_result["data"]:
                        initial_response["host_ip"] = sse_result["data"]["host_ip"]
                else:
                    initial_response["status"] = "failed"
            
            return initial_response
    
    async def configure_vm(
        self,
        vm_uuid: str,
        compose_file_path: str,
        env_config_path: str
    ) -> Dict[str, Any]:
        """Configure a VM with Docker Compose and environment configuration.
        
        Args:
            vm_uuid (str): The UUID of the VM to configure
            compose_file_path (str): Path to the Docker Compose file
            env_config_path (str): Path to the environment configuration YAML file
            
        Returns:
            Dict[str, Any]: Configuration response
            
        Raises:
            aiohttp.ClientError: If the API request fails.
            FileNotFoundError: If the files don't exist.
        """
        headers = {"X-API-Key": self.api_key}
        
        # Validate files exist
        if not os.path.exists(compose_file_path):
            raise FileNotFoundError(f"Docker Compose file not found: {compose_file_path}")
        if not os.path.exists(env_config_path):
            raise FileNotFoundError(f"Environment config file not found: {env_config_path}")
        
        # Read and parse YAML files
        with open(compose_file_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        with open(env_config_path, 'r') as f:
            env_config = yaml.safe_load(f)
        
        # Send parsed YAML content as JSON
        request_data = {
            "job_uuid": vm_uuid,
            "compose_config": compose_config,
            "env_config": env_config
        }
        
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/configure",
            json=request_data,
            headers=headers,
        ) as response:
            await self._handle_response_error(response)
            initial_response = await response.json()
            
            # Wait for SSE completion if correlation_id is provided
            correlation_id = initial_response.get("correlation_id")
            if correlation_id:
                logger.info(f"Waiting for VM configuration to complete (correlation_id: {correlation_id})")
                sse_result = await self._listen_for_sse_result(correlation_id, 300)  # 5 minute timeout
                
                # Update the response with actual status
                if sse_result.get('success'):
                    initial_response["status"] = "configured"
                    initial_response["message"] = sse_result.get('message', 'VM configuration completed successfully')
                else:
                    initial_response["status"] = "failed"
                    initial_response["message"] = sse_result.get('message', 'VM configuration failed')
            
            return initial_response
    
    async def get_vm_url(self, vm_uuid: str) -> str:
        """Get the public URL for a VM.
        
        Args:
            vm_uuid (str): The UUID of the VM
            
        Returns:
            str: The public URL for the VM
            
        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If VM not found.
        """
        # TODO: Implement actual API call
        # Mock response for now
        return f"https://{vm_uuid}.sims.plato.so"
    
    async def save_vm_snapshot(
        self, 
        vm_uuid: str, 
        snapshot_name: Optional[str] = None,
        service: str = "default",
        version: str = "latest",
        timeout: int = 1800
    ) -> Dict[str, Any]:
        """Save a snapshot of a VM.
        
        Args:
            vm_uuid (str): The UUID of the VM
            snapshot_name (Optional[str]): Optional name for the snapshot
            service (str): Service name
            version (str): Version
            timeout (int): Snapshot timeout
            
        Returns:
            Dict[str, Any]: Snapshot creation response
            
        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If VM not found.
        """
        headers = {"X-API-Key": self.api_key}
        
        request_data = {
            "service": service,
            "version": version,
            "snapshot_name": snapshot_name,
            "timeout": timeout
        }
        
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/{vm_uuid}/snapshot",
            json=request_data,
            headers=headers,
        ) as response:
            await self._handle_response_error(response)
            initial_response = await response.json()
            
            # Wait for SSE completion
            correlation_id = initial_response.get("correlation_id")
            if correlation_id:
                logger.info(f"Waiting for snapshot creation to complete (correlation_id: {correlation_id})")
                sse_result = await self._listen_for_sse_result(correlation_id, timeout)
                
                # Update the response with actual status
                if sse_result.get('success'):
                    initial_response["status"] = "completed"
                    if "data" in sse_result:
                        snapshot_data = sse_result["data"]
                        if "snapshot_dir" in snapshot_data:
                            initial_response["snapshot_dir"] = snapshot_data["snapshot_dir"]
                        if "snapshot_s3_uri" in snapshot_data:
                            initial_response["snapshot_s3_uri"] = snapshot_data["snapshot_s3_uri"]
                else:
                    initial_response["status"] = "failed"
            
            return initial_response
    
    async def close_vm(self, vm_uuid: str) -> Dict[str, Any]:
        """Close and terminate a VM.
        
        Args:
            vm_uuid (str): The UUID of the VM to close
            
        Returns:
            Dict[str, Any]: VM termination response
            
        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If VM not found.
        """
        headers = {"X-API-Key": self.api_key}
        
        async with self.http_session.delete(
            f"{self.base_url}/public-build/vm/{vm_uuid}",
            headers=headers,
        ) as response:
            await self._handle_response_error(response)
            initial_response = await response.json()
            
            # Wait for SSE completion
            correlation_id = initial_response.get("correlation_id")
            if correlation_id:
                logger.info(f"Waiting for VM termination to complete (correlation_id: {correlation_id})")
                sse_result = await self._listen_for_sse_result(correlation_id, 300)  # 5 minute timeout
                
                # Update the response with actual status
                if sse_result.get('success'):
                    initial_response["status"] = "terminated"
                else:
                    initial_response["status"] = "failed"
            
            return initial_response
    
    async def list_active_vms(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all active VMs for the user.
        
        Args:
            service (Optional[str]): Filter by service name
        
        Returns:
            List[Dict[str, Any]]: List of active VMs
            
        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        
        params = {}
        if service:
            params["service"] = service
        
        async with self.http_session.get(
            f"{self.base_url}/public-build/vm/list",
            params=params,
            headers=headers,
        ) as response:
            await self._handle_response_error(response)
            response_data = await response.json()
            return response_data.get("vms", [])
    
    async def execute_vm_command(
        self, 
        vm_uuid: str, 
        container_name: str, 
        command: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Execute a command in a Docker container within a VM.
        
        Args:
            vm_uuid (str): The UUID of the VM
            container_name (str): Name of the Docker container
            command (str): Command to execute
            timeout (int): Command timeout in seconds
            
        Returns:
            Dict[str, Any]: Command execution response
            
        Raises:
            aiohttp.ClientError: If the API request fails.
            PlatoClientError: If VM or container not found.
        """
        headers = {"X-API-Key": self.api_key}
        
        request_data = {
            "container_name": container_name,
            "command": command,
            "timeout": timeout
        }
        
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/{vm_uuid}/execute",
            json=request_data,
            headers=headers,
        ) as response:
            await self._handle_response_error(response)
            initial_response = await response.json()
            
            # Wait for SSE completion
            correlation_id = initial_response.get("correlation_id")
            if correlation_id:
                logger.info(f"Waiting for command execution to complete (correlation_id: {correlation_id})")
                sse_result = await self._listen_for_sse_result(correlation_id, timeout)
                
                # Update the response with actual command results
                if sse_result.get('success'):
                    if "data" in sse_result:
                        command_data = sse_result["data"]
                        if "stdout" in command_data:
                            initial_response["stdout"] = command_data["stdout"]
                        if "stderr" in command_data:
                            initial_response["stderr"] = command_data["stderr"]
                        # Note: exit_code and execution_time_ms might be in the SSE data too
                else:
                    initial_response["stderr"] = sse_result.get("message", "Command execution failed")
                    initial_response["exit_code"] = 1
            
            return initial_response
    
    async def list_registry_simulators(self) -> List[Dict[str, Any]]:
        """List all simulators in the registry filtered by organization.
        
        Returns:
            List[Dict[str, Any]]: List of simulator registry items
            
        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/simulator/list-by-org", headers=headers
        ) as response:
            await self._handle_response_error(response)
            return await response.json()

