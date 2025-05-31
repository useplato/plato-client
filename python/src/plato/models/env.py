import os
from plato.models.task import CustomEvalConfig
from pydantic import Field
from plato.models import PlatoTask, EvaluationResult
from typing import Coroutine, List, Optional, Type, Dict, Any, TYPE_CHECKING
import time
import asyncio
import random
import logging
from plato.exceptions import PlatoClientError

logger = logging.getLogger(__name__)

# Using TYPE_CHECKING for proper type annotation without circular imports
if TYPE_CHECKING:
    from plato.sdk import Plato



class PlatoEnvironment:
    """A base environment class for Plato that handles task execution and state management.

    This class provides the core interface for creating, managing, and interacting with
    task environments. It implements an async context manager pattern and defines the
    basic contract that all Plato environments must fulfill.

    Attributes:
        _client (Plato): The client instance for interacting with the environment
        _current_task (Optional[PlatoTask]): The task currently being executed
        id (str): Unique identifier for this environment instance (job ID)
        _run_session_id (Optional[str]): The ID of the active run session, set after reset
        _heartbeat_task (Optional[asyncio.Task]): Task for sending periodic heartbeats
    """

    _current_task: Optional[PlatoTask] = Field(
        description="The current task for the environment", default=None
    )
    _client: "Plato" = Field(description="The client for the environment")
    id: str = Field(description="The ID for the environment (job ID)")
    _run_session_id: Optional[str] = Field(
        description="The ID of the active run session", default=None
    )
    _heartbeat_task: Optional[asyncio.Task] = None
    _heartbeat_interval: int = 30  # seconds
    _sim_job_id: Optional[str] = Field(
        description="The ID of the simulation job", default=None
    )

    def __init__(self, client: "Plato", id: str, sim_job_id: Optional[str] = None):
        self._client = client
        self.id = id
        self._run_session_id = None
        self._heartbeat_task = None
        self._sim_job_id = sim_job_id

    async def wait_for_ready(self, timeout: Optional[float] = None) -> None:
        """Wait for the environment to be ready.

        This method checks both the job status and worker health until everything is ready.
        Uses exponential backoff with jitter for polling to reduce server load.

        Args:
            timeout (Optional[float]): Maximum time to wait in seconds before raising an error.
                                     If None, will wait indefinitely.

        Raises:
            RuntimeError: If the environment fails to start within the timeout period.
        """
        start_time = time.time()
        base_delay = 0.5  # Starting delay in seconds
        max_delay = 8.0  # Maximum delay between retries

        # wait for the job to be running
        current_delay = base_delay
        while True:
            status = await self._client.get_job_status(self.id)
            if status["status"].lower() == "running":
                break

            # Add jitter (±25% of current delay)
            jitter = random.uniform(-0.25 * current_delay, 0.25 * current_delay)
            await asyncio.sleep(current_delay + jitter)

            if timeout and time.time() - start_time > timeout:
                raise RuntimeError(
                    "Environment failed to start - job never entered running state"
                )

            # Exponential backoff
            current_delay = min(current_delay * 2, max_delay)
            logger.debug(f"Waiting for job {self.id} to be running: {current_delay} seconds")

        # wait for the worker to be ready and healthy
        current_delay = base_delay  # Reset delay for worker health check
        while True:
            worker_status = await self._client.get_worker_ready(self.id)
            if worker_status["ready"]:
                break

            # Add jitter (±25% of current delay)
            jitter = random.uniform(-0.25 * current_delay, 0.25 * current_delay)
            await asyncio.sleep(current_delay + jitter)

            if timeout and time.time() - start_time > timeout:
                error_msg = worker_status.get("error", "Unknown error")
                raise RuntimeError(
                    f"Environment failed to start - worker not ready: {error_msg}"
                )

            # Exponential backoff
            current_delay = min(current_delay * 2, max_delay)
            logger.debug(f"Waiting for worker {self.id} to be ready: {current_delay} seconds")

         # Start the heartbeat task if not already running
        await self._start_heartbeat()

    async def __aenter__(self):
        """Enter the async context manager.

        Calls make() to initialize the environment and returns self.

        Returns:
            PlatoEnvironment: The initialized environment instance.
        """
        await self.wait_for_ready()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Type[BaseException]],
    ) -> None:
        """Exit the async context manager.

        Performs cleanup by calling close() when the context manager exits.

        Args:
            exc_type: The type of the exception that was raised, if any
            exc_val: The instance of the exception that was raised, if any
            exc_tb: The traceback of the exception that was raised, if any
        """
        await self.close()

    async def get_cdp_url(self) -> str:
        """Get the Chrome DevTools Protocol URL for this environment's session.

        Returns:
            str: The CDP URL for connecting to this environment's browser session.

        Raises:
            PlatoClientError: If no active run session exists.
        """
        if not self._run_session_id:
            raise PlatoClientError("No active run session. Call reset() first.")
        return await self._client.get_cdp_url(self.id)

    async def reset(self, task: Optional[PlatoTask] = None, agent_version: Optional[str] = None) -> str:
        """Reset the environment with an optional new task.

        Args:
            task (Optional[PlatoTask]): The new task to set up the environment for.

        Returns:
            None: The environment is reset and a new run session is created.
        """
        response = await self._client.reset_environment(self.id, task, agent_version)
        if task:
            self._current_task = task

        if not response["success"]:
            raise PlatoClientError(response["error"])

        # Store the run session ID from the response
        self._run_session_id = response["data"]["run_session_id"]
        if not self._run_session_id:
            raise PlatoClientError("Failed to reset environment. Please try again.")

        return self._run_session_id



    async def _heartbeat_loop(self) -> None:
        """Background task that periodically sends heartbeats to keep the environment active."""
        try:
            while True:
                try:
                    await self._client.send_heartbeat(self.id)
                    logger.debug(f"Heartbeat sent for job {self.id}")
                except Exception as e:
                    # Log the error but continue trying
                    logger.error(f"Heartbeat error for job {self.id}: {e}")
                await asyncio.sleep(self._heartbeat_interval)
        except asyncio.CancelledError:
            # Task was cancelled, clean exit
            pass
        except Exception as e:
            # Unexpected error
            logger.error(f"Heartbeat task failed with error: {e} for job {self.id}")

    async def _start_heartbeat(self) -> None:
        """Start the heartbeat background task if not already running."""
        # Cancel any existing heartbeat task
        await self._stop_heartbeat()

        # Start a new heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _stop_heartbeat(self) -> None:
        """Stop the heartbeat background task if it's running."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                # Wait for the task to be cancelled
                await self._heartbeat_task
            except asyncio.CancelledError:
                # This is expected when cancelling the task
                pass
            except Exception as e:
                # Log any unexpected errors
                logger.error(f"Error stopping heartbeat task for job {self.id}: {e}")
            finally:
                self._heartbeat_task = None

    async def get_state(self) -> Dict[str, Any]:
        """Get the current state of the environment.

        Returns:
            Dict[str, Any]: A dictionary representing the current state of the environment.

        Raises:
            PlatoClientError: If no active run session exists.
        """
        if not self._run_session_id:
            raise PlatoClientError("No active run session. Call reset() first.")
        return await self._client.get_environment_state(self.id)

    async def get_state_mutations(self) -> List[Dict[str, Any]]:
        """Get a list of state mutations that have occurred in the environment.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing state changes.

        Raises:
            PlatoClientError: If no active run session exists.
        """
        state = await self.get_state()
        return state.get("mutations", [])

    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """Get a value from a nested dictionary using dotted notation.

        Args:
            data: The dictionary to search in
            key_path: A string with dot-separated keys, can include list indices with []

        Returns:
            The value at the specified path

        Example:
            data = {"a": {"b": [{"c": 1}, {"c": 2}]}}
            _get_nested_value(data, "a.b[1].c") -> 2
        """
        current = data
        for part in key_path.split('.'):
            if '[' in part:
                # Handle list index access
                key, idx_str = part.split('[')
                idx = int(idx_str.rstrip(']'))
                current = current[key][idx]
            else:
                current = current[part]
        return current

    async def get_evaluation_result(self) -> EvaluationResult:
        """Evaluate whether the current task has been completed successfully.

        This method evaluates task completion based on the evaluation configuration
        specified in the task. It supports two types of evaluation:
        1. State mutation matching - checks if required state mutations occurred
           using dotted notation for nested paths (e.g., "browser.url" or "elements[0].text")
        2. Custom evaluation - uses a provided scoring function

        If no evaluation config is specified, defaults to checking the completed flag
        in the environment state.

        Returns:
            EvaluationResult: Contains success status and reason for failure if applicable.

        Raises:
            PlatoClientError: If no active run session exists.
        """
        if not self._run_session_id:
            raise PlatoClientError("No active run session. Call reset() first.")

        if not self._current_task or not self._current_task.eval_config:
            logger.warning(
                f"No evaluation config found for task: {self._current_task.name}"
            )
            raise PlatoClientError("No evaluation config found for task")

        eval_config = self._current_task.eval_config

        if isinstance(eval_config, CustomEvalConfig):
            # Get current state for custom evaluation
            state = await self.get_state()

            try:
                # Run custom evaluation function, expecting (bool, str) tuple
                result = await eval_config.score_fn(state)
                if isinstance(result, Coroutine):
                    result = await result
                if isinstance(result, tuple):
                    success, reason = result
                    return EvaluationResult(success=success, reason=None if success else reason)
                else:
                    # Handle legacy score functions that return just a boolean
                    return EvaluationResult(
                        success=bool(result),
                        reason=None if result else "Custom evaluation failed"
                    )
            except Exception as e:
                return EvaluationResult(
                    success=False,
                    reason=f"Custom evaluation error: {str(e)}"
                )

        else:
            return EvaluationResult(
                success=False,
                reason=f"Unknown evaluation type: {eval_config.type}"
            )

    async def evaluate(self, agent_version: Optional[str] = None) -> EvaluationResult:
        if not self._run_session_id:
            raise PlatoClientError("No active run session. Call reset() first.")

        eval_config = self._current_task.eval_config
        if isinstance(eval_config, CustomEvalConfig):
            evaluation_result = await self.get_evaluation_result()
            state = await self.get_state()
            state = state.get('state', {})
            mutations = state.get('mutations', [])
            if self._run_session_id:
                await self._client.post_evaluation_result(self._run_session_id, evaluation_result, agent_version, mutations)
            return evaluation_result
        else:
            # call /evaluate endpoint
            response = await self._client.evaluate(self._run_session_id, agent_version)
            result = response['result']
            return EvaluationResult(
                success=result.get('correct', False),
                reason=result.get('reason', None),
                diffs=result.get('diffs', None),
                expected_mutations=result.get('expected_mutations', None),
                actual_mutations=result.get('actual_mutations', None),
            )


    async def log(self, log: dict, type: str = "info") -> None:
        """Log a message to the environment.

        Args:
            log (dict): The log to log.
        """
        if not self._run_session_id:
            raise PlatoClientError("No active run session. Call reset() first.")
        await self._client.log(self._run_session_id, log, type)

    async def get_live_view_url(self) -> str:
        """Get the URL for accessing the live view of the environment.

        The live view provides a browser-based view of the environment through noVNC.

        Returns:
            str: The URL for accessing the live view of the environment.

        Raises:
            PlatoClientError: If no active run session exists or if the worker is not ready.
            aiohttp.ClientError: If the API request fails.
        """
        if not self._run_session_id:
            raise PlatoClientError("No active run session. Call reset() first.")
        return await self._client.get_live_view_url(self.id)


    async def get_session_url(self) -> str:
        """Get the URL for accessing the session of the environment.
        """
        if not self._run_session_id:
            raise PlatoClientError("No active run session. Call reset() first.")
        root_url = self._client.base_url.split("/api")[0]
        return os.path.join(root_url, "sessions", f"{self._run_session_id}/")

    async def close(self) -> None:
        """Clean up and close the environment.

        This method handles cleanup of resources by closing the environment
        through the API client and stopping the heartbeat task.
        """
        # Stop sending heartbeats
        await self._stop_heartbeat()

        # Close the environment through the API
        await self._client.close_environment(self.id)
