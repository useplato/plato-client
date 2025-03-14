from pydantic import Field
from plato.models import PlatoTask
from typing import List, Optional, Type, Dict, Any
import time
import asyncio
from plato.exceptions import PlatoClientError


class PlatoEnvironment:
    """A base environment class for Plato that handles task execution and state management.

    This class provides the core interface for creating, managing, and interacting with
    task environments. It implements an async context manager pattern and defines the
    basic contract that all Plato environments must fulfill.

    Attributes:
        _client (Plato): The client instance for interacting with the environment
        _current_task (Optional[PlatoTask]): The task currently being executed
        id (str): Unique identifier for this environment instance (job ID)
    """

    _current_task: Optional[PlatoTask] = Field(
        description="The current task for the environment", default=None
    )
    _client: "Plato" = Field(description="The client for the environment")
    id: str = Field(description="The ID for the environment (job ID)")

    def __init__(self, client: "Plato", id: str):
        self._client = client
        self.id = id

    async def wait_for_ready(self, timeout: Optional[float] = None) -> None:
        """Wait for the environment to be ready.

        This method checks both the job status and worker health until everything is ready.

        Args:
            timeout (Optional[float]): Maximum time to wait in seconds before raising an error.
                                     If None, will wait indefinitely.

        Raises:
            RuntimeError: If the environment fails to start within the timeout period.
        """
        start_time = time.time()

        # wait for the job to be running
        while True:
            status = await self._client.get_job_status(self.id)
            if status["status"].lower() == "running":
                break
            await asyncio.sleep(0.1)
            if timeout and time.time() - start_time > timeout:
                raise RuntimeError(
                    "Environment failed to start - job never entered running state"
                )

        # wait for the worker to be ready and healthy
        while True:
            worker_status = await self._client.get_worker_ready(self.id)
            if worker_status["ready"]:
                break
            await asyncio.sleep(0.1)
            if timeout and time.time() - start_time > timeout:
                error_msg = worker_status.get("error", "Unknown error")
                raise RuntimeError(
                    f"Environment failed to start - worker not ready: {error_msg}"
                )

        # wait for the cdp url to be ready
        while True:
            try:
                cdp_url = await self._client.get_cdp_url(self.id)
                if cdp_url:
                    break
            except PlatoClientError:
                await asyncio.sleep(0.1)
            if timeout and time.time() - start_time > timeout:
                raise RuntimeError("Environment failed to start - cdp url not ready")

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
        """
        return await self._client.get_cdp_url(self.id)

    async def reset(self, task: Optional[PlatoTask] = None) -> None:
        """Reset the environment with an optional new task.

        Args:
            task (Optional[PlatoTask]): The new task to set up the environment for.
        """
        await self._client.reset_environment(self.id, task)
        if task:
            self._current_task = task

    async def get_state(self) -> Dict[str, Any]:
        """Get the current state of the environment.

        Returns:
            Dict[str, Any]: A dictionary representing the current state of the environment.
        """
        return await self._client.get_environment_state(self.id)

    async def get_state_mutations(self) -> List[Dict[str, Any]]:
        """Get a list of state mutations that have occurred in the environment.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing state changes.
        """
        state = await self.get_state()
        return state.get("mutations", [])

    async def evaluate(self) -> bool:
        """Evaluate whether the current task has been completed successfully.

        Returns:
            bool: True if the task is completed successfully, False otherwise.
        """
        state = await self.get_state()
        return state.get("completed", False)

    async def close(self) -> None:
        """Clean up and close the environment.

        This method handles cleanup of resources by closing the environment
        through the API client.
        """
        await self._client.close_environment(self.id)
