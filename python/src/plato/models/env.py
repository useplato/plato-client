from pydantic import BaseModel, Field
from plato.client import PlatoClient
from plato.models import PlatoTask
from typing import List, Optional, Type

class PlatoEnvironment(BaseModel):
    """A base environment class for Plato that handles task execution and state management.

    This class provides the core interface for creating, managing, and interacting with
    task environments. It implements an async context manager pattern and defines the
    basic contract that all Plato environments must fulfill.

    Attributes:
        _client (PlatoClient): The client instance for interacting with the environment
        _current_task (Optional[PlatoTask]): The task currently being executed
        _session_id (Optional[str]): Unique identifier for the current session
        id (str): Unique identifier for this environment instance
    """

    _client: PlatoClient = Field(description="The client for the environment")
    _current_task: Optional[PlatoTask] = Field(description="The current task for the environment", default=None)
    _session_id: Optional[str] = Field(description="The session ID for the environment", default=None)

    id: str = Field(description="The ID for the environment")

    async def make(self):
        """Initialize and set up the environment.
        
        This method should be implemented by subclasses to perform any necessary
        setup or initialization of the environment.
        
        Raises:
            NotImplementedError: This base method must be implemented by subclasses.
        """
        raise NotImplementedError("Make is not implemented for this environment")
    
    async def __aenter__(self):
        """Enter the async context manager.
        
        Calls make() to initialize the environment and returns self.
        
        Returns:
            PlatoEnvironment: The initialized environment instance.
        """
        await self.make()
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], 
                        exc_val: Optional[BaseException], 
                        exc_tb: Optional[Type[BaseException]]) -> None:
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
        return self._client.get_cdp_url(self.session_id)

    async def reset(self, task: PlatoTask) -> None:
        """Reset the environment with a new task.
        
        Args:
            task (PlatoTask): The new task to set up the environment for.
            
        Raises:
            NotImplementedError: This base method must be implemented by subclasses.
        """
        self.task = task
        raise NotImplementedError("Reset is not implemented for this environment")

    async def get_state(self) -> dict:
        """Get the current state of the environment.
        
        Returns:
            dict: A dictionary representing the current state of the environment.
            
        Raises:
            NotImplementedError: This base method must be implemented by subclasses.
        """
        raise NotImplementedError("Get state is not implemented for this environment")

    async def get_state_mutations(self) -> List[dict]:
        """Get a list of state mutations that have occurred in the environment.
        
        Returns:
            List[dict]: A list of dictionaries representing state changes.
            
        Raises:
            NotImplementedError: This base method must be implemented by subclasses.
        """
        raise NotImplementedError("Get state mutations is not implemented for this environment")

    async def evaluate(self) -> bool:
        """Evaluate whether the current task has been completed successfully.
        
        Returns:
            bool: True if the task is completed successfully, False otherwise.
            
        Raises:
            NotImplementedError: This base method must be implemented by subclasses.
        """
        raise NotImplementedError("Evaluate is not implemented for this environment")

    async def close(self) -> None:
        """Clean up and close the environment.
        
        This method should handle any necessary cleanup of resources when
        the environment is no longer needed.
        
        Raises:
            NotImplementedError: This base method must be implemented by subclasses.
        """
        raise NotImplementedError("Close is not implemented for this environment")  