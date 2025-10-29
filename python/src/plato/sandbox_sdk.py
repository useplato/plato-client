"""
Plato Sandbox SDK for Python

Simple Python wrapper around the Go Sandbox SDK using C bindings.
"""

import ctypes
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from plato.models.sandbox import (
    Sandbox,
    SimConfigDataset,
    DBConfig,
    CreateSnapshotRequest,
    CreateSnapshotResponse,
    StartWorkerRequest,
    StartWorkerResponse,
    SimulatorListItem,
)

# Set up logging
logger = logging.getLogger("plato.sandbox_sdk")
logger.setLevel(logging.INFO)

# Only add handler if none exists (avoid duplicate logs)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[PLATO-PY] %(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


# Find the shared library
def _find_lib():
    """Find the libplato shared library"""
    # Try different extensions for different platforms
    extensions = [".dylib", ".so", ".dll"]

    # First, try to find it in the same directory as this file (for packaged distribution)
    package_dir = Path(__file__).resolve().parent
    for ext in extensions:
        lib_path = package_dir / f"libplato{ext}"
        if lib_path.exists():
            return str(lib_path)

    # Fallback: Try the development location (sdk/bindings/c)
    # python/src/plato/sandbox_sdk.py -> ../../../sdk/bindings/c
    bindings_dir = package_dir.parent.parent.parent / "sdk" / "bindings" / "c"
    for ext in extensions:
        lib_path = bindings_dir / f"libplato{ext}"
        if lib_path.exists():
            return str(lib_path)

    raise FileNotFoundError(
        f"Could not find libplato shared library. Searched in:\n"
        f"  1. Package directory: {package_dir}\n"
        f"  2. Development directory: {bindings_dir}\n"
        f"Run: ./scripts/build-python-bindings.sh"
    )


# Load the shared library (do this lazily to avoid import-time errors)
_lib = None
_lib_path = None

def _get_lib():
    """Get the loaded library, loading it if necessary"""
    global _lib, _lib_path
    if _lib is None:
        _lib_path = _find_lib()
        _lib = ctypes.CDLL(_lib_path)

        # Define function signatures
        # Use c_void_p for return types so we can manually manage memory
        _lib.plato_new_client.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_new_client.restype = ctypes.c_void_p

        _lib.plato_create_sandbox.argtypes = [
            ctypes.c_char_p,  # clientID
            ctypes.c_char_p,  # configJSON
            ctypes.c_char_p,  # dataset
            ctypes.c_char_p,  # alias
            ctypes.c_char_p,  # artifactID
            ctypes.c_char_p,  # service
            ctypes.c_int,     # timeout
        ]
        _lib.plato_create_sandbox.restype = ctypes.c_void_p

        _lib.plato_delete_sandbox.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_delete_sandbox.restype = ctypes.c_void_p

        _lib.plato_create_snapshot.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_create_snapshot.restype = ctypes.c_void_p

        _lib.plato_create_snapshot_with_cleanup.argtypes = [
            ctypes.c_char_p,  # clientID
            ctypes.c_char_p,  # publicID
            ctypes.c_char_p,  # jobGroupID
            ctypes.c_char_p,  # requestJSON
            ctypes.c_char_p,  # dbConfigJSON
        ]
        _lib.plato_create_snapshot_with_cleanup.restype = ctypes.c_void_p

        _lib.plato_start_worker.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_start_worker.restype = ctypes.c_void_p

        _lib.plato_list_simulators.argtypes = [ctypes.c_char_p]
        _lib.plato_list_simulators.restype = ctypes.c_void_p

        _lib.plato_get_simulator_versions.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_get_simulator_versions.restype = ctypes.c_void_p

        _lib.plato_monitor_operation.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        _lib.plato_monitor_operation.restype = ctypes.c_void_p

        _lib.plato_gitea_get_credentials.argtypes = [ctypes.c_char_p]
        _lib.plato_gitea_get_credentials.restype = ctypes.c_void_p

        _lib.plato_gitea_list_simulators.argtypes = [ctypes.c_char_p]
        _lib.plato_gitea_list_simulators.restype = ctypes.c_void_p

        _lib.plato_gitea_get_simulator_repo.argtypes = [ctypes.c_char_p, ctypes.c_int]
        _lib.plato_gitea_get_simulator_repo.restype = ctypes.c_void_p

        _lib.plato_gitea_create_simulator_repo.argtypes = [ctypes.c_char_p, ctypes.c_int]
        _lib.plato_gitea_create_simulator_repo.restype = ctypes.c_void_p

        _lib.plato_proxytunnel_start.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        _lib.plato_proxytunnel_start.restype = ctypes.c_void_p

        _lib.plato_proxytunnel_stop.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_proxytunnel_stop.restype = ctypes.c_void_p

        _lib.plato_proxytunnel_list.argtypes = [ctypes.c_char_p]
        _lib.plato_proxytunnel_list.restype = ctypes.c_void_p

        _lib.plato_gitea_push_to_hub.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_gitea_push_to_hub.restype = ctypes.c_void_p

        _lib.plato_gitea_merge_to_main.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_gitea_merge_to_main.restype = ctypes.c_void_p

        _lib.plato_setup_ssh.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_setup_ssh.restype = ctypes.c_void_p

        _lib.plato_free_string.argtypes = [ctypes.c_void_p]
        _lib.plato_free_string.restype = None

    return _lib


def _call_and_free(lib, result_ptr):
    """Helper to extract string from C pointer and free it"""
    if not result_ptr:
        raise RuntimeError("Got null pointer from C function")
    try:
        # Cast void pointer to char pointer and extract string
        s = ctypes.cast(result_ptr, ctypes.c_char_p).value
        if s is None:
            raise RuntimeError("Got null string from C function")
        return s.decode('utf-8')
    finally:
        # Always free the C string
        lib.plato_free_string(result_ptr)


class PlatoSandboxClient:
    """
    Plato Sandbox SDK Client

    Python wrapper for managing VM sandboxes via the Plato API.

    Examples:
        # Initialize client with API key (uses default base URL)
        >>> client = PlatoSandboxClient('your-api-key')

        # Or with custom base URL
        >>> client = PlatoSandboxClient('your-api-key', base_url='https://custom.plato.so/api')

        # Create sandbox from configuration (waits until ready by default)
        >>> from plato.models.sandbox import SimConfigDataset, SimConfigCompute, SimConfigMetadata
        >>> config = SimConfigDataset(
        ...     compute=SimConfigCompute(
        ...         cpus=1, memory=512, disk=10240,
        ...         app_port=8080, plato_messaging_port=7000
        ...     ),
        ...     metadata=SimConfigMetadata(name='My Sandbox')
        ... )
        >>> sandbox = client.create_sandbox(config=config)
        >>> print(f"Sandbox ready! Status: {sandbox.status}")  # status = "running"

        # Create sandbox from artifact ID (also waits by default)
        >>> sandbox = client.create_sandbox(artifact_id="art_123456")
        >>> print(f"URL: {sandbox.url}, Status: {sandbox.status}")

        # Close sandbox when done
        >>> client.close_sandbox(sandbox.public_id)
    """

    def __init__(self, api_key: str, base_url: str = "https://plato.so/api"):
        """
        Initialize the Plato Sandbox client

        Args:
            api_key: Your Plato API key
            base_url: Base URL of the Plato API (default: 'https://plato.so/api')
        """
        logger.debug(f"Initializing PlatoSandboxClient with base_url={base_url}")

        # Helpful check: detect if user accidentally passed URL as api_key (old signature)
        if api_key.startswith('http://') or api_key.startswith('https://'):
            raise ValueError(
                "It looks like you passed a URL as the api_key. "
                "The signature has changed to: PlatoSandboxClient(api_key, base_url='https://plato.so/api'). "
                f"Did you mean: PlatoSandboxClient('{base_url}', base_url='{api_key}')?"
            )

        self._base_url = base_url
        self._sandbox_configs = {}  # Cache configs by sandbox public_id
        lib = _get_lib()
        result_ptr = lib.plato_new_client(
            base_url.encode('utf-8'),
            api_key.encode('utf-8')
        )
        self._client_id = _call_and_free(lib, result_ptr)
        logger.info(f"Created PlatoSandboxClient with client_id={self._client_id}")

    def create_sandbox(
        self,
        config: Optional[SimConfigDataset] = None,
        dataset: str = "base",
        alias: str = "sandbox",
        artifact_id: Optional[str] = None,
        service: str = "",
        wait: bool = True,
        timeout: int = 600,
        sandbox_timeout: int | None = None
    ) -> Sandbox:
        """
        Create a new VM sandbox

        You can create a sandbox in two ways:
        1. From a configuration: Provide `config` with full VM configuration
        2. From an artifact: Provide `artifact_id` to launch from a snapshot

        Args:
            config: Sandbox configuration (SimConfigDataset or dict). If not provided with artifact_id,
                   a default boilerplate config will be used.
            dataset: Dataset name (default: 'base')
            alias: Human-readable alias (default: 'sandbox')
            artifact_id: Optional artifact ID to launch from snapshot
            service: Service name
            wait: If True, blocks until sandbox is ready (default: True)
            timeout: Timeout in seconds when wait=True (default: 600)
            sandbox_timeout: Timeout in seconds for sandbox creation on server side (default: 1200)

        Returns:
            Sandbox object with public_id, url, status, etc.

        Raises:
            ValueError: If neither config nor artifact_id is provided
            RuntimeError: If sandbox creation fails or times out

        Examples:
            # Create from configuration
            >>> config = SimConfigDataset(
            ...     compute=SimConfigCompute(cpus=1, memory=512, disk=10240,
            ...                             app_port=8080, plato_messaging_port=7000),
            ...     metadata=SimConfigMetadata(name="Test")
            ... )
            >>> sandbox = client.create_sandbox(config=config)

            # Create from artifact ID and wait until ready (default behavior)
            >>> sandbox = client.create_sandbox(artifact_id="art_123456")
            >>> print(f"Sandbox ready at {sandbox.url}")

            # Create without waiting (for async workflows)
            >>> sandbox = client.create_sandbox(artifact_id="art_123456", wait=False)
            >>> # Do other work...
            >>> client.wait_until_ready(sandbox.correlation_id)
        """
        # Validation: Must provide either config or artifact_id
        if config is None and artifact_id is None:
            raise ValueError(
                "Must provide either 'config' or 'artifact_id'. "
                "Use 'config' to create a new sandbox from configuration, "
                "or 'artifact_id' to create from an existing snapshot."
            )

        # If artifact_id is provided but no config, use a default boilerplate config
        # TODO(API): The API should fetch the proper config from the artifact metadata
        # instead of requiring the client to send a boilerplate config
        if config is None and artifact_id is not None:
            # Default boilerplate config - actual config should be fetched from artifact on API side
            config_dict = {
                "compute": {
                    "cpus": 1,
                    "memory": 512,
                    "disk": 10240,
                    "app_port": 8080,
                    "plato_messaging_port": 7000
                },
                "metadata": {
                    "name": "Default"
                }
            }
            config_json = json.dumps(config_dict)
        elif config is not None:
            # Convert config to dict if it's a Pydantic model
            # Use mode='json' to properly serialize enums to their values
            config_dict = config.model_dump(mode='json', exclude_none=True)
            config_json = json.dumps(config_dict)
        else:
            config_json = "{}"

        logger.info(f"Creating sandbox: artifact_id={artifact_id}, service={service}, dataset={dataset}, sandbox_timeout={sandbox_timeout}")
        lib = _get_lib()
        result_ptr = lib.plato_create_sandbox(
            self._client_id.encode('utf-8'),
            config_json.encode('utf-8'),
            dataset.encode('utf-8'),
            alias.encode('utf-8'),
            artifact_id.encode('utf-8') if artifact_id else b'',
            service.encode('utf-8'),
            ctypes.c_int(sandbox_timeout if sandbox_timeout is not None else -1),
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to create sandbox: {response['error']}")
            raise RuntimeError(f"Failed to create sandbox: {response['error']}")

        sandbox = Sandbox(**response)
        logger.info(f"Sandbox created: public_id={sandbox.public_id}, job_group_id={sandbox.job_group_id}")
        logger.debug(f"Automatic heartbeat started for job_group_id={sandbox.job_group_id}")

        # Cache the config and dataset for later use (e.g., in setup_ssh)
        if config is not None:
            self._sandbox_configs[sandbox.public_id] = {
                'config': config,
                'dataset': dataset
            }

        # Wait for sandbox to be ready if requested
        if wait and sandbox.correlation_id:
            logger.info(f"Waiting for sandbox {sandbox.public_id} to be ready (timeout={timeout}s)")
            self.wait_until_ready(sandbox.correlation_id, timeout=timeout)
            # Update status to "running" once ready
            sandbox.status = "running"
            logger.info(f"Sandbox {sandbox.public_id} is ready")

        return sandbox

    def close_sandbox(self, public_id: str) -> None:
        """
        Close a VM sandbox

        Args:
            public_id: Public ID of the sandbox to close

        Raises:
            RuntimeError: If closing fails
        """
        logger.info(f"Closing sandbox: public_id={public_id}")
        lib = _get_lib()
        result_ptr = lib.plato_delete_sandbox(
            self._client_id.encode('utf-8'),
            public_id.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to close sandbox {public_id}: {response['error']}")
            raise RuntimeError(f"Failed to close sandbox: {response['error']}")

        # Clean up cached config
        self._sandbox_configs.pop(public_id, None)

        logger.info(f"Sandbox {public_id} closed successfully (heartbeat stopped automatically)")

    def create_snapshot(
        self,
        public_id: str,
        request: CreateSnapshotRequest
    ) -> CreateSnapshotResponse:
        """
        Create a snapshot of a sandbox

        Args:
            public_id: Public ID of the sandbox
            request: Snapshot request (CreateSnapshotRequest or dict) with 'service', 'dataset', optional 'git_hash'

        Returns:
            CreateSnapshotResponse with artifact_id, s3_uri, status, etc.

        Raises:
            RuntimeError: If snapshot creation fails

        Example:
            >>> request = CreateSnapshotRequest(service="web", dataset="base")
            >>> snapshot = client.create_snapshot(sandbox.public_id, request)
            >>> print(snapshot.artifact_id)
        """
        # Convert to dict if Pydantic model
        # Use mode='json' to properly serialize enums to their values
        request_dict = request.model_dump(mode='json', exclude_none=True)
        request_json = json.dumps(request_dict)

        lib = _get_lib()
        result_ptr = lib.plato_create_snapshot(
            self._client_id.encode('utf-8'),
            public_id.encode('utf-8'),
            request_json.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            raise RuntimeError(f"Failed to create snapshot: {response['error']}")

        return CreateSnapshotResponse(**response)

    def create_snapshot_with_cleanup(
        self,
        public_id: str,
        job_group_id: str,
        request: CreateSnapshotRequest,
        db_config: Optional[Union[DBConfig, Dict[str, Any]]] = None
    ) -> CreateSnapshotResponse:
        """
        Create a snapshot with pre-snapshot database cleanup

        This performs database cleanup (clears audit_log and env state) before creating the snapshot.
        Useful for creating clean snapshots without residual data from testing/development.

        Args:
            public_id: Public ID of the sandbox
            job_group_id: Job group ID of the sandbox
            request: Snapshot request (CreateSnapshotRequest) with 'service', 'dataset', optional 'git_hash'
            db_config: Optional database configuration (DBConfig or dict) with:
                - db_type: "postgresql" or "mysql"
                - user: Database user
                - password: Database password
                - dest_port: Database port (e.g., 5432 for PostgreSQL, 3306 for MySQL)
                - databases: List of database names to clean

        Returns:
            CreateSnapshotResponse with artifact_id, s3_uri, status, etc.

        Raises:
            RuntimeError: If snapshot creation or cleanup fails

        Example:
            >>> from plato.models.sandbox import DBConfig, CreateSnapshotRequest
            >>> 
            >>> # Using Pydantic model (recommended)
            >>> db_config = DBConfig(
            ...     db_type="postgresql",
            ...     user="postgres",
            ...     password="password",
            ...     dest_port=5432,
            ...     databases=["postgres", "myapp"]
            ... )
            >>> request = CreateSnapshotRequest(service="web", dataset="base")
            >>> snapshot = client.create_snapshot_with_cleanup(
            ...     sandbox.public_id,
            ...     sandbox.job_group_id,
            ...     request,
            ...     db_config
            ... )
            >>> print(snapshot.artifact_id)
            >>>
            >>> # Or using dict (also supported)
            >>> db_config = {
            ...     "db_type": "postgresql",
            ...     "user": "postgres",
            ...     "password": "password",
            ...     "dest_port": 5432,
            ...     "databases": ["postgres", "myapp"]
            ... }
            >>> snapshot = client.create_snapshot_with_cleanup(
            ...     sandbox.public_id,
            ...     sandbox.job_group_id,
            ...     request,
            ...     db_config
            ... )
        """
        logger.info(f"Creating snapshot with cleanup for sandbox {public_id}")

        # Convert request to dict if Pydantic model
        request_dict = request.model_dump(mode='json', exclude_none=True)
        request_json = json.dumps(request_dict)

        # Convert db_config to JSON (or null if not provided)
        if db_config is None:
            db_config_json = "null"
        elif isinstance(db_config, DBConfig):
            db_config_dict = db_config.model_dump(mode='json', exclude_none=True)
            db_config_json = json.dumps(db_config_dict)
        else:
            # Assume it's a dict
            db_config_json = json.dumps(db_config)

        lib = _get_lib()
        result_ptr = lib.plato_create_snapshot_with_cleanup(
            self._client_id.encode('utf-8'),
            public_id.encode('utf-8'),
            job_group_id.encode('utf-8'),
            request_json.encode('utf-8'),
            db_config_json.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to create snapshot with cleanup: {response['error']}")
            raise RuntimeError(f"Failed to create snapshot with cleanup: {response['error']}")

        logger.info(f"Snapshot created successfully: {response.get('artifact_id')}")
        return CreateSnapshotResponse(**response)

    def start_worker(
        self,
        public_id: str,
        request: Union[StartWorkerRequest, Dict[str, Any]]
    ) -> StartWorkerResponse:
        """
        Start a Plato worker in a sandbox

        Args:
            public_id: Public ID of the sandbox
            request: Worker request (StartWorkerRequest or dict) with 'service', 'dataset',
                    'plato_dataset_config', optional 'timeout'

        Returns:
            StartWorkerResponse with status, correlation_id, timestamp

        Raises:
            RuntimeError: If worker start fails

        Example:
            >>> request = StartWorkerRequest(
            ...     dataset="base",
            ...     plato_dataset_config=config
            ... )
            >>> response = client.start_worker(sandbox.public_id, request)
            >>> print(response.status)
        """
        # Convert to dict if Pydantic model
        if isinstance(request, StartWorkerRequest):
            # Use mode='json' to properly serialize enums to their values
            request_dict = request.model_dump(mode='json', exclude_none=True)
        else:
            request_dict = request
        request_json = json.dumps(request_dict)

        lib = _get_lib()
        result_ptr = lib.plato_start_worker(
            self._client_id.encode('utf-8'),
            public_id.encode('utf-8'),
            request_json.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            raise RuntimeError(f"Failed to start worker: {response['error']}")

        return StartWorkerResponse(**response)

    def list_simulators(self) -> List[SimulatorListItem]:
        """
        List all available simulators

        Returns:
            List of SimulatorListItem objects with name, description, artifact_id

        Raises:
            RuntimeError: If listing fails

        Example:
            >>> simulators = client.list_simulators()
            >>> for sim in simulators:
            ...     print(f"{sim.name}: {sim.description}")
        """
        lib = _get_lib()
        result_ptr = lib.plato_list_simulators(
            self._client_id.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)

        # Check if it's an error response (dict with 'error' key)
        response = json.loads(result_str)
        if isinstance(response, dict) and 'error' in response:
            raise RuntimeError(f"Failed to list simulators: {response['error']}")

        return [SimulatorListItem(**item) for item in response]

    def get_simulator_versions(self, simulator_name: str) -> List[Dict[str, Any]]:
        """
        Get all versions for a specific simulator

        Args:
            simulator_name: Name of the simulator (e.g., 'espocrm')

        Returns:
            List of version dicts with artifact_id, version, dataset, created_at

        Raises:
            RuntimeError: If getting versions fails

        Example:
            >>> versions = client.get_simulator_versions("espocrm")
            >>> for v in versions:
            ...     print(f"Version {v['version']}: {v['artifact_id']}")
        """
        lib = _get_lib()
        result_ptr = lib.plato_get_simulator_versions(
            self._client_id.encode('utf-8'),
            simulator_name.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)

        # Check if it's an error response (dict with 'error' key)
        response = json.loads(result_str)
        if isinstance(response, dict) and 'error' in response:
            raise RuntimeError(f"Failed to get versions: {response['error']}")

        return response

    def wait_until_ready(
        self,
        correlation_id: str,
        timeout: int = 600
    ) -> None:
        """
        Wait until an operation completes by monitoring SSE events

        This function blocks until the operation completes or times out.
        Used after creating a sandbox to wait for it to be ready.

        Args:
            correlation_id: Correlation ID from the sandbox creation response
            timeout: Timeout in seconds (default: 600 = 10 minutes)

        Raises:
            RuntimeError: If operation fails or times out

        Example:
            >>> sandbox = client.create_sandbox(artifact_id="art_123")
            >>> client.wait_until_ready(sandbox.correlation_id)
            >>> print(f"Sandbox ready at {sandbox.url}")
        """
        lib = _get_lib()
        result_ptr = lib.plato_monitor_operation(
            self._client_id.encode('utf-8'),
            correlation_id.encode('utf-8'),
            ctypes.c_int(timeout)
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            raise RuntimeError(f"Operation failed: {response['error']}")

    def get_gitea_credentials(self) -> Dict[str, str]:
        """
        Get Gitea credentials for the organization.

        Returns:
            Dict with 'username', 'password', 'org_name'

        Raises:
            RuntimeError: If getting credentials fails
        """
        logger.debug("Getting Gitea credentials")
        lib = _get_lib()
        result_ptr = lib.plato_gitea_get_credentials(
            self._client_id.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to get Gitea credentials: {response['error']}")
            raise RuntimeError(f"Failed to get credentials: {response['error']}")

        logger.info(f"Got Gitea credentials for user: {response.get('username')}, org: {response.get('org_name')}")
        return response

    def list_gitea_simulators(self) -> List[Dict[str, Any]]:
        """
        List all simulators with Gitea repository information.

        Returns:
            List of simulator dicts with 'id', 'name', 'has_repo', etc.

        Raises:
            RuntimeError: If listing fails
        """
        logger.debug("Listing Gitea simulators")
        lib = _get_lib()
        result_ptr = lib.plato_gitea_list_simulators(
            self._client_id.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if isinstance(response, dict) and 'error' in response:
            logger.error(f"Failed to list Gitea simulators: {response['error']}")
            raise RuntimeError(f"Failed to list simulators: {response['error']}")

        logger.info(f"Listed {len(response)} Gitea simulators")
        return response

    def get_gitea_repository(self, simulator_id: int) -> Dict[str, Any]:
        """
        Get repository information for a simulator.

        Args:
            simulator_id: Simulator ID

        Returns:
            Dict with 'name', 'clone_url', 'ssh_url', etc.

        Raises:
            RuntimeError: If getting repository fails
        """
        logger.debug(f"Getting Gitea repository for simulator_id={simulator_id}")
        lib = _get_lib()
        result_ptr = lib.plato_gitea_get_simulator_repo(
            self._client_id.encode('utf-8'),
            ctypes.c_int(simulator_id)
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to get repository for simulator {simulator_id}: {response['error']}")
            raise RuntimeError(f"Failed to get repository: {response['error']}")

        logger.info(f"Got repository for simulator {simulator_id}: {response.get('name')} (clone_url: {response.get('clone_url')})")
        return response

    def create_gitea_repository(self, simulator_id: int) -> Dict[str, Any]:
        """
        Create a repository for a simulator.

        Args:
            simulator_id: Simulator ID

        Returns:
            Dict with 'name', 'clone_url', 'ssh_url', etc.

        Raises:
            RuntimeError: If creating repository fails
        """
        logger.debug(f"Creating Gitea repository for simulator_id={simulator_id}")
        lib = _get_lib()
        result_ptr = lib.plato_gitea_create_simulator_repo(
            self._client_id.encode('utf-8'),
            ctypes.c_int(simulator_id)
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to create repository for simulator {simulator_id}: {response['error']}")
            raise RuntimeError(f"Failed to create repository: {response['error']}")

        logger.info(f"Created repository for simulator {simulator_id}: {response.get('name')} (clone_url: {response.get('clone_url')})")
        return response

    def start_proxy_tunnel(self, public_id: str, remote_port: int, local_port: int = 0) -> Dict[str, Any]:
        """
        Start a proxy tunnel to connect to a port on the sandbox.

        Args:
            public_id: Public ID of the sandbox
            remote_port: Port on the remote sandbox to connect to
            local_port: Local port to bind to (0 = auto-select)

        Returns:
            Dict with 'tunnel_id' and 'local_port'

        Raises:
            RuntimeError: If starting the tunnel fails
        """
        logger.info(f"Starting proxy tunnel: public_id={public_id}, remote_port={remote_port}, local_port={local_port}")
        lib = _get_lib()
        result_ptr = lib.plato_proxytunnel_start(
            self._client_id.encode('utf-8'),
            public_id.encode('utf-8'),
            ctypes.c_int(remote_port),
            ctypes.c_int(local_port)
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to start proxy tunnel: {response['error']}")
            raise RuntimeError(f"Failed to start proxy tunnel: {response['error']}")

        logger.info(f"Proxy tunnel started: tunnel_id={response['tunnel_id']}, local_port={response['local_port']}")
        return response

    def stop_proxy_tunnel(self, tunnel_id: str) -> None:
        """
        Stop a running proxy tunnel.

        Args:
            tunnel_id: ID of the tunnel to stop

        Raises:
            RuntimeError: If stopping the tunnel fails
        """
        logger.info(f"Stopping proxy tunnel: tunnel_id={tunnel_id}")
        lib = _get_lib()
        result_ptr = lib.plato_proxytunnel_stop(
            self._client_id.encode('utf-8'),
            tunnel_id.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to stop proxy tunnel: {response['error']}")
            raise RuntimeError(f"Failed to stop proxy tunnel: {response['error']}")

        logger.info(f"Proxy tunnel stopped: tunnel_id={tunnel_id}")

    def list_proxy_tunnels(self) -> List[Dict[str, Any]]:
        """
        List all active proxy tunnels.

        Returns:
            List of tunnel dicts with 'ID', 'LocalPort', 'RemotePort', 'PublicID'

        Raises:
            RuntimeError: If listing fails
        """
        logger.debug("Listing proxy tunnels")
        lib = _get_lib()
        result_ptr = lib.plato_proxytunnel_list(
            self._client_id.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if isinstance(response, dict) and 'error' in response:
            logger.error(f"Failed to list proxy tunnels: {response['error']}")
            raise RuntimeError(f"Failed to list proxy tunnels: {response['error']}")

        logger.info(f"Listed {len(response)} proxy tunnels")
        return response

    def push_to_gitea(self, service_name: str, source_dir: str = "") -> Dict[str, Any]:
        """
        Push local code to Gitea repository on a timestamped branch.

        Args:
            service_name: Name of the service/simulator
            source_dir: Source directory to push (empty string = current directory)

        Returns:
            Dict with 'RepoURL', 'CloneCmd', 'BranchName'

        Raises:
            RuntimeError: If push fails
        """
        logger.info(f"Pushing to Gitea: service={service_name}, source_dir={source_dir}")
        lib = _get_lib()
        result_ptr = lib.plato_gitea_push_to_hub(
            self._client_id.encode('utf-8'),
            service_name.encode('utf-8'),
            source_dir.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to push to Gitea: {response['error']}")
            raise RuntimeError(f"Failed to push to Gitea: {response['error']}")

        logger.info(f"Pushed to Gitea: branch={response.get('BranchName')}")
        return response

    def merge_to_main(self, service_name: str, branch_name: str) -> str:
        """
        Merge a workspace branch to main and return the git hash.

        Args:
            service_name: Name of the service/simulator
            branch_name: Branch name to merge

        Returns:
            Git commit hash

        Raises:
            RuntimeError: If merge fails
        """
        logger.info(f"Merging to main: service={service_name}, branch={branch_name}")
        lib = _get_lib()
        result_ptr = lib.plato_gitea_merge_to_main(
            self._client_id.encode('utf-8'),
            service_name.encode('utf-8'),
            branch_name.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            logger.error(f"Failed to merge to main: {response['error']}")
            raise RuntimeError(f"Failed to merge to main: {response['error']}")

        git_hash = response.get('git_hash', '')
        logger.info(f"Merged to main: git_hash={git_hash}")
        return git_hash

    def setup_ssh(
        self,
        sandbox: Sandbox,
        config: Optional[SimConfigDataset] = None,
        dataset: Optional[str] = None,
        local_port: int = 2200,
        username: str = "plato"
    ) -> Dict[str, str]:
        """
        Setup SSH configuration for a sandbox and get connection information.

        This method:
        1. Generates a new ED25519 SSH key pair
        2. Creates SSH config file with ProxyCommand for tunnel connection
        3. Uploads the public key to the sandbox
        4. Returns SSH connection details

        Args:
            sandbox: Sandbox object with public_id and job_group_id
            config: Sandbox configuration (optional if sandbox was created with this client)
            dataset: Dataset name (optional, will use cached value or default to "base")
            local_port: Local port for SSH connection (default: 2200)
            username: SSH username (default: "plato")

        Returns:
            Dict with:
                - 'ssh_command': Full SSH command to connect
                - 'ssh_host': SSH host identifier (e.g., "sandbox-1")
                - 'ssh_config_path': Path to SSH config file
                - 'public_key': Generated SSH public key
                - 'private_key_path': Path to private key file
                - 'public_id': Sandbox public ID
                - 'correlation_id': Correlation ID for monitoring setup

        Raises:
            RuntimeError: If SSH setup fails or config not found

        Example:
            >>> # If sandbox was created with this client, config is cached
            >>> sandbox = client.create_sandbox(config=config)
            >>> ssh_info = client.setup_ssh(sandbox)
            >>>
            >>> # Or explicitly provide config
            >>> ssh_info = client.setup_ssh(sandbox, config=config, dataset="base")
            >>> print(f"Connect with: {ssh_info['ssh_command']}")
        """
        logger.info(f"Setting up SSH for sandbox {sandbox.public_id}")

        # Try to get cached config if not provided
        if config is None:
            cached = self._sandbox_configs.get(sandbox.public_id)
            if cached is None:
                raise RuntimeError(
                    f"No cached config found for sandbox {sandbox.public_id}. "
                    "Please provide config and dataset explicitly."
                )
            config = cached['config']
            if dataset is None:
                dataset = cached['dataset']

        # Default dataset if still not set
        if dataset is None:
            dataset = "base"

        # Convert config to JSON
        config_dict = config.model_dump(mode='json', exclude_none=True)
        config_json = json.dumps(config_dict)

        lib = _get_lib()
        result_ptr = lib.plato_setup_ssh(
            self._client_id.encode('utf-8'),
            self._base_url.encode('utf-8'),
            ctypes.c_int(local_port),
            sandbox.public_id.encode('utf-8'),
            username.encode('utf-8'),
            config_json.encode('utf-8'),
            dataset.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        try:
            response = json.loads(result_str)
        except:
            logger.error(f"Couldn't parse response: {result_str}")


        if 'error' in response:
            logger.error(f"Failed to setup SSH: {response['error']}")
            raise RuntimeError(f"Failed to setup SSH: {response['error']}")

        logger.info(f"SSH setup complete for {sandbox.public_id}: {response['ssh_command']}")
        return response
