"""
Plato SDK for Python

Python SDK for managing Plato sandboxes using Protocol Buffers for models
and C bindings for API operations.

Example:
    >>> from plato_sdk import PlatoClient
    >>> import plato_pb2
    >>>
    >>> client = PlatoClient("your-api-key")
    >>>
    >>> # Create config using protobuf
    >>> config = plato_pb2.SimConfigDataset(
    ...     compute=plato_pb2.SimConfigCompute(cpus=2, memory=2048, disk=20480),
    ...     metadata=plato_pb2.SimConfigMetadata(
    ...         name="My Sandbox",
    ...         description="Test sandbox"
    ...     )
    ... )
    >>>
    >>> # Create sandbox
    >>> sandbox = client.sandbox_create(config, "default", "my-sandbox")
    >>> print(f"Created: {sandbox.public_id}")
    >>>
    >>> # Start heartbeat
    >>> client.sandbox_start_heartbeat(sandbox.job_group_id, 30)
    >>>
    >>> # Cleanup
    >>> client.sandbox_stop_heartbeat(sandbox.job_group_id)
    >>> client.sandbox_delete_vm(sandbox.public_id)
"""

import ctypes
import platform
from pathlib import Path
from typing import Optional
from google.protobuf import json_format
import plato_pb2


def _find_library():
    """Find the Plato shared library."""
    system = platform.system()

    if system == "Darwin":
        lib_names = ["libplato.dylib"]
    elif system == "Linux":
        lib_names = ["libplato.so"]
    elif system == "Windows":
        lib_names = ["plato.dll"]
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    # Search paths
    search_paths = [
        Path(__file__).parent.parent / "c",  # Development location
        Path("/usr/local/lib"),
        Path("/usr/lib"),
        Path.cwd(),
    ]

    for path in search_paths:
        for lib_name in lib_names:
            lib_path = path / lib_name
            if lib_path.exists():
                return str(lib_path)

    raise RuntimeError(
        f"Could not find Plato library. Searched: {lib_names} in {search_paths}"
    )


# Load the shared library
_lib_path = _find_library()
_lib = ctypes.CDLL(_lib_path)


# Define C structures
class CSandbox(ctypes.Structure):
    _fields_ = [
        ("job_id", ctypes.c_char_p),
        ("public_id", ctypes.c_char_p),
        ("job_group_id", ctypes.c_char_p),
        ("url", ctypes.c_char_p),
        ("status", ctypes.c_char_p),
        ("correlation_id", ctypes.c_char_p),
    ]


class CError(ctypes.Structure):
    _fields_ = [
        ("error", ctypes.c_char_p),
        ("code", ctypes.c_int),
    ]


# Define function signatures
_lib.PlatoInit.argtypes = [ctypes.c_char_p]
_lib.PlatoInit.restype = ctypes.c_int64

_lib.PlatoFree.argtypes = [ctypes.c_int64]
_lib.PlatoFree.restype = None

_lib.PlatoSandboxCreate.argtypes = [
    ctypes.c_int64,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.POINTER(CError)),
]
_lib.PlatoSandboxCreate.restype = ctypes.POINTER(CSandbox)

_lib.PlatoSandboxMonitor.argtypes = [
    ctypes.c_int64,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.POINTER(ctypes.POINTER(CError)),
]
_lib.PlatoSandboxMonitor.restype = None

_lib.PlatoSandboxStartHeartbeat.argtypes = [
    ctypes.c_int64,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.POINTER(ctypes.POINTER(CError)),
]
_lib.PlatoSandboxStartHeartbeat.restype = None

_lib.PlatoSandboxStopHeartbeat.argtypes = [ctypes.c_char_p]
_lib.PlatoSandboxStopHeartbeat.restype = None

_lib.PlatoSandboxSendHeartbeat.argtypes = [
    ctypes.c_int64,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.POINTER(CError)),
]
_lib.PlatoSandboxSendHeartbeat.restype = None

_lib.PlatoSandboxDeleteVM.argtypes = [
    ctypes.c_int64,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.POINTER(CError)),
]
_lib.PlatoSandboxDeleteVM.restype = None

_lib.PlatoFreeSandbox.argtypes = [ctypes.POINTER(CSandbox)]
_lib.PlatoFreeSandbox.restype = None

_lib.PlatoFreeError.argtypes = [ctypes.POINTER(CError)]
_lib.PlatoFreeError.restype = None


class PlatoError(Exception):
    """Exception raised for Plato API errors."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


def _check_error(err_ptr):
    """Check for errors and raise if present."""
    if err_ptr:
        err = err_ptr.contents
        msg = err.error.decode("utf-8") if err.error else "Unknown error"
        code = err.code
        _lib.PlatoFreeError(err_ptr)
        raise PlatoError(msg, code)


def _csandbox_to_proto(csandbox: CSandbox) -> plato_pb2.Sandbox:
    """Convert C sandbox to protobuf."""
    return plato_pb2.Sandbox(
        job_id=csandbox.job_id.decode("utf-8") if csandbox.job_id else "",
        public_id=csandbox.public_id.decode("utf-8") if csandbox.public_id else "",
        job_group_id=csandbox.job_group_id.decode("utf-8") if csandbox.job_group_id else "",
        url=csandbox.url.decode("utf-8") if csandbox.url else "",
        status=csandbox.status.decode("utf-8") if csandbox.status else "",
        correlation_id=csandbox.correlation_id.decode("utf-8") if csandbox.correlation_id else "",
    )


class PlatoClient:
    """
    Plato SDK Client.

    Example:
        >>> client = PlatoClient("your-api-key")
        >>> config = plato_pb2.SimConfigDataset(...)
        >>> sandbox = client.sandbox_create(config, "default", "my-sandbox")
    """

    def __init__(self, api_key: str):
        """Initialize client with API key."""
        self._handle = _lib.PlatoInit(api_key.encode("utf-8"))

    def __del__(self):
        """Clean up the client."""
        if hasattr(self, "_handle"):
            _lib.PlatoFree(self._handle)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    def sandbox_create(
        self,
        config: plato_pb2.SimConfigDataset,
        dataset: str,
        alias: str,
        artifact_id: Optional[str] = None,
        service: str = "",
    ) -> plato_pb2.Sandbox:
        """
        Create a new sandbox.

        Args:
            config: Sandbox configuration (protobuf SimConfigDataset)
            dataset: Dataset name
            alias: Alias for the sandbox
            artifact_id: Optional artifact ID
            service: Optional service name

        Returns:
            Sandbox protobuf message

        Example:
            >>> config = plato_pb2.SimConfigDataset(
            ...     compute=plato_pb2.SimConfigCompute(cpus=2, memory=2048),
            ...     metadata=plato_pb2.SimConfigMetadata(name="My Sandbox")
            ... )
            >>> sandbox = client.sandbox_create(config, "default", "my-sandbox")
        """
        # Convert protobuf to JSON
        config_json = json_format.MessageToJson(config, preserving_proto_field_name=True)

        err = ctypes.POINTER(CError)()
        result = _lib.PlatoSandboxCreate(
            self._handle,
            config_json.encode("utf-8"),
            dataset.encode("utf-8"),
            alias.encode("utf-8"),
            artifact_id.encode("utf-8") if artifact_id else None,
            service.encode("utf-8"),
            ctypes.byref(err),
        )

        _check_error(err)

        if not result:
            raise PlatoError("Failed to create sandbox", 0)

        sandbox = _csandbox_to_proto(result.contents)
        _lib.PlatoFreeSandbox(result)
        return sandbox

    def sandbox_monitor(self, correlation_id: str, timeout_seconds: int = 600):
        """Monitor an operation until completion."""
        err = ctypes.POINTER(CError)()
        _lib.PlatoSandboxMonitor(
            self._handle,
            correlation_id.encode("utf-8"),
            timeout_seconds,
            ctypes.byref(err),
        )
        _check_error(err)

    def sandbox_start_heartbeat(self, job_group_id: str, interval: int = 30):
        """Start automatic heartbeat (interval in seconds)."""
        err = ctypes.POINTER(CError)()
        _lib.PlatoSandboxStartHeartbeat(
            self._handle,
            job_group_id.encode("utf-8"),
            interval,
            ctypes.byref(err),
        )
        _check_error(err)

    def sandbox_stop_heartbeat(self, job_group_id: str):
        """Stop automatic heartbeat."""
        _lib.PlatoSandboxStopHeartbeat(job_group_id.encode("utf-8"))

    def sandbox_send_heartbeat(self, job_group_id: str):
        """Send a single heartbeat."""
        err = ctypes.POINTER(CError)()
        _lib.PlatoSandboxSendHeartbeat(
            self._handle,
            job_group_id.encode("utf-8"),
            ctypes.byref(err),
        )
        _check_error(err)

    def sandbox_delete_vm(self, public_id: str):
        """Delete a VM by public ID."""
        err = ctypes.POINTER(CError)()
        _lib.PlatoSandboxDeleteVM(
            self._handle,
            public_id.encode("utf-8"),
            ctypes.byref(err),
        )
        _check_error(err)
