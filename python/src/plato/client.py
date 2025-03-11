from typing import Optional
import aiohttp
import plato.config as config
from plato.models import PlatoTask, PlatoEnvironment

class PlatoClient:
    """Client for interacting with the Plato API.

    This class provides methods to create and manage Plato environments, handle API authentication,
    and manage HTTP sessions.

    Attributes:
        api_key (str): The API key used for authentication with Plato API.
        base_url (str): The base URL of the Plato API.
        http_session (Optional[aiohttp.ClientSession]): The aiohttp session for making HTTP requests.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize a new PlatoClient.

        Args:
            api_key (Optional[str]): The API key for authentication. If not provided,
                falls back to the key from config.
        """
        self.api_key = api_key or config.api_key
        self.base_url = config.base_url
        self.http_session: Optional[aiohttp.ClientSession] = None

    @property
    def http_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp client session.

        Returns:
            aiohttp.ClientSession: The active HTTP client session.
        """
        if self.http_session is None:
            self.http_session = aiohttp.ClientSession()
        return self.http_session

    async def close(self):
        """Close the aiohttp client session if it exists."""
        if self.http_session is not None:
            await self.http_session.close()
            self.http_session = None

    async def make_environment(self, task: PlatoTask) -> PlatoEnvironment:
        """Create a new Plato environment for the given task.

        Args:
            task (PlatoTask): The task to create an environment for.

        Returns:
            PlatoEnvironment: The created environment instance.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with self.http_session.post(
            f"{self.base_url}/environments",
            json=task.dict(),
            headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return PlatoEnvironment(
                _client=self,
                _current_task=task,
                session_id=data["session_id"]
            )

    async def get_cdp_url(self, session_id: str) -> str:
        """Get the Chrome DevTools Protocol URL for a session.

        Args:
            session_id (str): The ID of the session to get the CDP URL for.

        Returns:
            str: The CDP URL for the session.

        Raises:
            aiohttp.ClientError: If the API request fails.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with self.http_session.get(
            f"{self.base_url}/environments/{session_id}/cdp_url",
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.text()
