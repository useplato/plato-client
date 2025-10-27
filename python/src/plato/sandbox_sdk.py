"""
Plato Sandbox SDK for Python

Simple Python wrapper around the Go Sandbox SDK using C bindings.
"""

import ctypes
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


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
        ]
        _lib.plato_create_sandbox.restype = ctypes.c_void_p

        _lib.plato_delete_sandbox.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_delete_sandbox.restype = ctypes.c_void_p

        _lib.plato_create_snapshot.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_create_snapshot.restype = ctypes.c_void_p

        _lib.plato_start_worker.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_start_worker.restype = ctypes.c_void_p

        _lib.plato_list_simulators.argtypes = [ctypes.c_char_p]
        _lib.plato_list_simulators.restype = ctypes.c_void_p

        _lib.plato_get_simulator_versions.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.plato_get_simulator_versions.restype = ctypes.c_void_p

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

    Simple Python wrapper for managing VM sandboxes.

    Example:
        >>> client = PlatoSandboxClient('https://api.plato.so', 'your-api-key')
        >>> config = {
        ...     'compute': {'cpus': 1, 'memory': 512, 'disk': 10240,
        ...                 'app_port': 8080, 'plato_messaging_port': 7000},
        ...     'metadata': {'name': 'Test'},
        ...     'services': {},
        ...     'listeners': {}
        ... }
        >>> sandbox = client.create_sandbox(config)
        >>> print(sandbox['public_id'])
    """

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the Plato Sandbox client

        Args:
            base_url: Base URL of the Plato API (e.g., 'https://api.plato.so')
            api_key: Your Plato API key
        """
        lib = _get_lib()
        result_ptr = lib.plato_new_client(
            base_url.encode('utf-8'),
            api_key.encode('utf-8')
        )
        self._client_id = _call_and_free(lib, result_ptr)

    def create_sandbox(
        self,
        config: Dict[str, Any],
        dataset: str = "base",
        alias: str = "sandbox",
        artifact_id: Optional[str] = None,
        service: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new VM sandbox

        Args:
            config: Sandbox configuration dict with compute, metadata, services, listeners
            dataset: Dataset name (default: 'base')
            alias: Human-readable alias (default: 'sandbox')
            artifact_id: Optional artifact ID to launch from snapshot
            service: Service name

        Returns:
            Dict with sandbox details including 'public_id', 'url', 'status'

        Raises:
            RuntimeError: If sandbox creation fails
        """
        config_json = json.dumps(config)

        lib = _get_lib()
        result_ptr = lib.plato_create_sandbox(
            self._client_id.encode('utf-8'),
            config_json.encode('utf-8'),
            dataset.encode('utf-8'),
            alias.encode('utf-8'),
            artifact_id.encode('utf-8') if artifact_id else b'',
            service.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            raise RuntimeError(f"Failed to create sandbox: {response['error']}")

        return response

    def delete_sandbox(self, public_id: str) -> None:
        """
        Delete a VM sandbox

        Args:
            public_id: Public ID of the sandbox to delete

        Raises:
            RuntimeError: If deletion fails
        """
        lib = _get_lib()
        result_ptr = lib.plato_delete_sandbox(
            self._client_id.encode('utf-8'),
            public_id.encode('utf-8')
        )

        result_str = _call_and_free(lib, result_ptr)
        response = json.loads(result_str)

        if 'error' in response:
            raise RuntimeError(f"Failed to delete sandbox: {response['error']}")

    def create_snapshot(
        self,
        public_id: str,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a snapshot of a sandbox

        Args:
            public_id: Public ID of the sandbox
            request: Dict with 'service', 'dataset', optional 'git_hash'

        Returns:
            Dict with snapshot details including 'artifact_id', 's3_uri'

        Raises:
            RuntimeError: If snapshot creation fails
        """
        request_json = json.dumps(request)

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

        return response

    def start_worker(
        self,
        public_id: str,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Start a Plato worker in a sandbox

        Args:
            public_id: Public ID of the sandbox
            request: Dict with 'service', 'dataset', 'plato_dataset_config', optional 'timeout'

        Returns:
            Dict with worker start details including 'status', 'correlation_id'

        Raises:
            RuntimeError: If worker start fails
        """
        request_json = json.dumps(request)

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

        return response

    def list_simulators(self) -> list:
        """
        List all available simulators

        Returns:
            List of simulator objects with id, name, description, etc.

        Raises:
            RuntimeError: If listing fails
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

        return response

    def get_simulator_versions(self, simulator_name: str) -> list:
        """
        Get all versions for a specific simulator

        Args:
            simulator_name: Name of the simulator (e.g., 'espocrm')

        Returns:
            List of version objects with artifact_id, version, dataset, created_at

        Raises:
            RuntimeError: If getting versions fails
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
