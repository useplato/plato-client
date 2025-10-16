from typing import Optional
import os
from plato.config import get_config
from plato.exceptions import PlatoClientError
from plato.models.build_models import (
    VMManagementResponse,
    VMManagementRequest,
    CreateVMResponse,
    CreateVMRequest,
    SetupSandboxRequest,
    SetupSandboxResponse,
    SimConfigDataset,
)

# Rich progress and console are not used here; keep minimal imports
import aiohttp
import logging
# no-op

logger = logging.getLogger(__name__)

config = get_config()


class PlatoSandboxSDK:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize a new Plato.

        Args:
            api_key (Optional[str]): The API key for authentication. If not provided,
                falls back to the key from config.
        """
        self.api_key = api_key or config.api_key
        self.base_url = base_url or config.base_url
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._debug = bool(os.getenv("PLATO_DEBUG", "").strip())

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
                error_message = (
                    error_data.get("error")
                    or error_data.get("message")
                    or str(error_data)
                )
            except (aiohttp.ContentTypeError, ValueError):
                # Fallback to status text if we can't parse JSON
                error_message = response.reason or f"HTTP {response.status}"

            raise PlatoClientError(f"HTTP {response.status}: {error_message}")

    async def snapshot(
        self,
        public_id: str,
    ) -> VMManagementResponse:
        """Create a snapshot of a VM.
        Args:
            public_id (str): The ID of the job to create a snapshot for.
        Returns:
            VMManagementResponse: The response from the server.
        Raises:
            PlatoClientError: If the API request fails.
        """
        headers = {"X-API-Key": self.api_key}
        if self._debug:
            logger.info(f"POST {self.base_url}/public-build/vm/{public_id}/snapshot")
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/{public_id}/snapshot",
            headers=headers,
        ) as snapshot_response:
            if self._debug:
                logger.info(f"<- {snapshot_response.status}")
            if snapshot_response.status == 200:
                try:
                    snapshot_data = VMManagementResponse.model_validate(
                        await snapshot_response.json()
                    )
                    return snapshot_data
                except Exception as e:
                    raise PlatoClientError(f"Failed to Validate snapshot response: {e}")
            else:
                error = await snapshot_response.text()
                raise PlatoClientError(f"Failed to create snapshot: {error}")

    async def start_services(
        self,
        public_id: str,
        dataset: str,
        dataset_config: SimConfigDataset,
    ) -> VMManagementResponse:
        headers = {"X-API-Key": self.api_key}

        if self._debug:
            logger.info(
                f"POST {self.base_url}/public-build/vm/{public_id}/start-services"
            )
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/{public_id}/start-services",
            headers=headers,
            json=VMManagementRequest(
                dataset=dataset,
                plato_dataset_config=dataset_config.model_dump(),
                timeout=120,  # Increase timeout to 2 minutes for services start
            ).model_dump(mode="json"),
        ) as services_response:
            if self._debug:
                logger.info(f"<- {services_response.status}")
            if services_response.status == 200:
                try:
                    services_data = VMManagementResponse.model_validate(
                        await services_response.json()
                    )
                    return services_data
                except Exception as e:
                    raise PlatoClientError(f"Failed to Validate services response: {e}")
            else:
                error = await services_response.text()
                raise PlatoClientError(f"Failed to start services: {error}")

    async def healthy_services(
        self,
        public_id: str,
        dataset: str,
        dataset_config: SimConfigDataset,
    ) -> VMManagementResponse:
        """Trigger services health check (async); returns correlation id only."""
        headers = {"X-API-Key": self.api_key}
        if self._debug:
            logger.info(
                f"GET {self.base_url}/public-build/vm/{public_id}/healthy-services"
            )
        async with self.http_session.get(
            f"{self.base_url}/public-build/vm/{public_id}/healthy-services",
            headers=headers,
            json=VMManagementRequest(
                dataset=dataset,
                plato_dataset_config=dataset_config.model_dump(),
            ).model_dump(mode="json"),
        ) as healthy_services_response:
            if self._debug:
                logger.info(f"<- {healthy_services_response.status}")
            if healthy_services_response.status == 200:
                try:
                    return VMManagementResponse.model_validate(
                        await healthy_services_response.json()
                    )
                except Exception as e:
                    raise PlatoClientError(
                        f"Failed to validate healthy services response: {e}"
                    )
            else:
                error = await healthy_services_response.text()
                raise PlatoClientError(f"Failed to check healthy services: {error}")

    async def start_worker(
        self,
        public_id: str,
        dataset: str,
        dataset_config: SimConfigDataset,
    ) -> VMManagementResponse:
        """Start listeners and plato worker with the dataset configuration."""
        headers = {"X-API-Key": self.api_key}
        if self._debug:
            logger.info(
                f"POST {self.base_url}/public-build/vm/{public_id}/start-worker"
            )
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/{public_id}/start-worker",
            headers=headers,
            json=VMManagementRequest(
                dataset=dataset,
                plato_dataset_config=dataset_config.model_dump(),
                timeout=120,  # Increase timeout to 2 minutes for worker start
            ).model_dump(mode="json"),
        ) as worker_response:
            if self._debug:
                logger.info(f"<- {worker_response.status}")
            if worker_response.status == 200:
                try:
                    worker_data = VMManagementResponse.model_validate(
                        await worker_response.json()
                    )
                    return worker_data
                except Exception as e:
                    raise PlatoClientError(f"Failed to Validate worker response: {e}")
            else:
                error = await worker_response.text()
                raise PlatoClientError(f"Failed to start worker: {error}")

    async def healthy_worker(self, public_id: str) -> VMManagementResponse:
        """Check the health status of the plato-worker service."""
        headers = {"X-API-Key": self.api_key}
        if self._debug:
            logger.info(
                f"GET {self.base_url}/public-build/vm/{public_id}/healthy-worker"
            )
        async with self.http_session.get(
            f"{self.base_url}/public-build/vm/{public_id}/healthy-worker",
            headers=headers,
        ) as healthy_worker_response:
            if self._debug:
                logger.info(f"<- {healthy_worker_response.status}")
            if healthy_worker_response.status == 200:
                try:
                    healthy_worker_data = VMManagementResponse.model_validate(
                        await healthy_worker_response.json()
                    )
                    return healthy_worker_data
                except Exception as e:
                    raise PlatoClientError(
                        f"Failed to Validate healthy worker response: {e}"
                    )
            else:
                error = await healthy_worker_response.text()
                raise PlatoClientError(f"Failed to check healthy worker: {error}")

    async def create_vm(
        self,
        sim_name: str,
        dataset_config: SimConfigDataset,
        git_hash: str,
        dataset: str,
        timeout: int,
        wait_time: int,
        alias: str,
    ) -> CreateVMResponse:
        """Create a VM instance and return the response for correlation monitoring."""
        headers = {"X-API-Key": self.api_key}
        if self._debug:
            logger.info(f"POST {self.base_url}/public-build/vm/create")
        async with self.http_session.post(
            f"{self.base_url}/public-build/vm/create",
            json=CreateVMRequest(
                dataset=dataset,
                plato_dataset_config=dataset_config.model_dump(),
                timeout=timeout,
                service=sim_name,
                git_hash=git_hash,
                wait_time=wait_time,
                alias=alias,
            ).model_dump(mode="json"),
            headers=headers,
        ) as vm_response:
            if self._debug:
                logger.info(f"<- {vm_response.status}")
            if vm_response.status == 200:
                try:
                    response_json = await vm_response.json()
                    if self._debug:
                        logger.info(f"create_vm response: {response_json}")
                    vm_data = CreateVMResponse.model_validate(response_json)
                    return vm_data
                except Exception as e:
                    # Print actual response for debugging
                    try:
                        logger.error(f"create_vm raw response: {response_json}")
                    except Exception:
                        pass
                    raise PlatoClientError(
                        f"Failed to Validate create VM response: {e}"
                    )
            else:
                error = await vm_response.text()
                raise PlatoClientError(f"Failed to create VM: {error}")

    async def setup_sandbox(
        self,
        public_id: str,
        clone_url: str,
        dataset: str,
        dataset_config: SimConfigDataset,
        local_public_key: str,
    ) -> SetupSandboxResponse:
        """Setup sandbox environment and return response for correlation monitoring."""
        headers = {"X-API-Key": self.api_key}
        if self._debug:
            logger.info(
                f"POST {self.base_url}/public-build/vm/{public_id}/setup-sandbox"
            )
        async with (
            self.http_session.post(
                f"{self.base_url}/public-build/vm/{public_id}/setup-sandbox",
                json=SetupSandboxRequest(
                    dataset=dataset,
                    plato_dataset_config=dataset_config,
                    clone_url=clone_url,
                    client_ssh_public_key=local_public_key,
                    chisel_port=6000,  # Legacy parameter required by backend, ignored by ProxyTunnel
                ).model_dump(mode="json"),
                headers=headers,
            ) as setup_response
        ):
            if self._debug:
                logger.info(f"<- {setup_response.status}")
            if setup_response.status == 200:
                try:
                    setup_response_data = SetupSandboxResponse.model_validate(
                        await setup_response.json()
                    )
                    return setup_response_data
                except Exception as e:
                    raise PlatoClientError(
                        f"Failed to Validate setup sandbox response: {e}"
                    )
            else:
                error = await setup_response.text()
                raise PlatoClientError(f"Failed to setup sandbox: {error}")
