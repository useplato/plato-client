"""This module provides classes and methods for interacting with the Plato API."""

import enum
from typing import Optional, TypeVar
from urllib.parse import urlparse

import requests
from pydantic import BaseModel

BASE_URL = "https://plato.so"

T = TypeVar("T", bound=BaseModel)

_type = type


class ParamType(str, enum.Enum):
    """Enumeration of possible parameter types for extraction."""

    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    DATE = "date"
    IMAGE = "image"


class ExtractParameter(BaseModel):
    """Model representing a parameter to be extracted."""

    name: str
    description: Optional[str] = ""
    type: ParamType
    isArray: bool = False
    elementHint: Optional[dict] = None
    subParameters: Optional[list["ExtractParameter"]]


class Plato:
    """Main class for interacting with the Plato API."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = BASE_URL,
        cookies: Optional[dict] = None,
    ):
        """Initialize a Plato instance.

        :param api_key: API key for authentication.
        :param base_url: Base URL for the Plato API.
        :param cookies: Optional cookies for session management.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.cookies = cookies

    class PlatoSession:
        """Handles a session with the Plato API."""

        def __init__(self, plato: "Plato"):
            """Initialize a PlatoSession instance.

            :param plato: An instance of the Plato class.
            """
            self.plato = plato
            self.session_id = None

        def __enter__(self):
            """Enter the runtime context related to this object."""
            self.start()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            """Exit the runtime context related to this object."""
            self.end()

        @property
        def api_url(self):
            """Construct the API URL based on the base URL."""
            url = urlparse(self.plato.base_url)
            return f"{url.scheme}://api.{url.netloc}"

        @property
        def chrome_ws_url(self):
            """Construct the WebSocket URL for Chrome based on the base URL."""
            url = urlparse(self.plato.base_url)
            return f"{'wss' if url.scheme == 'https' else 'ws'}://{url.netloc}/ws?session_id={self.session_id}"

        @property
        def browser_url(self):
            """Construct the browser URL based on the base URL."""
            url = urlparse(self.plato.base_url)
            return f"{url.scheme}://browser.{url.netloc}/plato?session_id={self.session_id}"

        def start(self):
            """Start a new session with the Plato API."""
            response = requests.post(
                f"{self.api_url}/start-session",
                headers={"Authorization": f"Bearer {self.plato.api_key}"},
                json={"cookies": self.plato.cookies},
            )
            response.raise_for_status()
            self.session_id = response.json()["session_id"]

            print("Started Plato browser session", self.browser_url)

        def end(self):
            """End the current session with the Plato API."""
            response = requests.post(
                f"{self.api_url}/end-session",
                headers={"Authorization": f"Bearer {self.plato.api_key}"},
                json={"session_id": self.session_id},
            )
            response.raise_for_status()
            return response.json()

        def navigate(self, url: str):
            """Navigate to a specified URL within the session.

            :param url: The URL to navigate to.
            """
            response = requests.post(
                f"{self.api_url}/navigate",
                headers={"Authorization": f"Bearer {self.plato.api_key}"},
                json={"session_id": self.session_id, "url": url},
            )
            response.raise_for_status()
            return response.json()

        def click(self, description: str):
            """Simulate a click action based on a description.

            :param description: Description of the element to click.
            """
            response = requests.post(
                f"{self.api_url}/click",
                headers={"Authorization": f"Bearer {self.plato.api_key}"},
                json={"session_id": self.session_id, "description": description},
            )
            response.raise_for_status()
            return response.json()

        def type(self, text: str):
            """Simulate typing text into an input field.

            :param text: The text to type.
            """
            response = requests.post(
                f"{self.api_url}/type",
                headers={"Authorization": f"Bearer {self.plato.api_key}"},
                json={"session_id": self.session_id, "text": text},
            )
            response.raise_for_status()
            return response.json()

        def extract(self, description: str, response_format: _type[T]) -> T:
            """Extract data based on a description and response format.

            :param description: Description of the data to extract.
            :param response_format: A Pydantic model class defining the structure of the data to be extracted.
            :return: An instance of the provided Pydantic model containing the extracted data.
            :type T: Type parameter that extends BaseModel
            """
            response = requests.post(
                f"{self.api_url}/extract",
                headers={"Authorization": f"Bearer {self.plato.api_key}"},
                json={
                    "session_id": self.session_id,
                    "description": description,
                    "response_format": response_format.model_json_schema(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return response_format(**data)

        def task(
            self,
            task: str,
            start_url: Optional[str] = None,
            response_format: Optional[_type[T]] = None,
        ) -> T:
            """Execute a task within the session.

            :param task: The task to execute.
            :param start_url: Optional starting URL for the task.
            :param response_format: Optional Pydantic model class defining the structure of the data to be extracted.
            :return: An instance of the provided Pydantic model containing the extracted data.
            :type T: Type parameter that extends BaseModel
            """
            response = requests.post(
                f"{self.api_url}/task",
                headers={"Authorization": f"Bearer {self.plato.api_key}"},
                json={
                    "session_id": self.session_id,
                    "task": task,
                    "start_url": start_url,
                    "response_format": response_format.model_json_schema()
                    if response_format
                    else None,
                },
            )
            response.raise_for_status()
            data = response.json()
            return response_format(**data) if response_format else data

        def monitor(self, url: str, **kwargs):
            """Monitor a specified URL for changes.

            :param url: The URL to monitor.
            """
            pass

        def job(self, job_id: str, **kwargs):
            """Retrieve information about a specific job.

            :param job_id: The ID of the job to retrieve.
            """
            pass

    def start_session(self) -> "PlatoSession":
        """Start a new Plato session."""
        session = self.PlatoSession(self)
        session.start()
        return session
