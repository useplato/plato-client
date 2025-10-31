"""
Plato Python SDK

A wrapper around the auto-generated Fern SDK with additional helper methods
that won't be lost during regeneration.
"""

from .client import PlatoClient, OperationTimeoutError, OperationFailedError
from .async_client import AsyncPlatoClient

# Re-export commonly used types from generated SDK
from ._generated.types import (
    OperationEvent,
    OperationEventType,
    Sandbox,
    Environment,
    CreateSandboxResponse,
)
from ._generated.core.request_options import RequestOptions

__all__ = [
    "PlatoClient",
    "AsyncPlatoClient",
    "OperationTimeoutError",
    "OperationFailedError",
    "OperationEvent",
    "OperationEventType",
    "Sandbox",
    "Environment",
    "CreateSandboxResponse",
    "RequestOptions",
]
__version__ = "0.1.0"


