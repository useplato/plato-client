# Plato Python SDK

A Python SDK wrapper for the Plato API that provides additional helper methods on top of the auto-generated Fern SDK. This package ensures that custom functionality persists even when the underlying generated SDK is regenerated.

## Features

- **SSE Monitoring Helpers**: Convenient methods for monitoring long-running operations
- **Future-Proof**: Wraps the generated SDK so custom code isn't lost during regeneration
- **Full API Access**: All methods from the generated SDK are available through inheritance
- **Async Support**: Both synchronous and asynchronous clients available

## Installation

```bash
pip install plato-sdk
```

Or install from source:

```bash
cd sdk/sdks/python
pip install -e .
```

## Quick Start

### Synchronous Client

```python
import sys
from pathlib import Path

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import PlatoClient, OperationFailedError, OperationTimeoutError

# Create client
client = PlatoClient(
    base_url="https://api.plato.so",
    headers={"X-API-Key": "your-api-key"}
)

# Monitor operation with 10 minute timeout
try:
    client.monitor_operation_sync("correlation-id-123", timeout_seconds=600)
    print("Operation completed successfully!")
except OperationTimeoutError:
    print("Operation timed out")
except OperationFailedError as e:
    print(f"Operation failed: {e}")
```

### Async Client

```python
import asyncio
import sys
from pathlib import Path

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import AsyncPlatoClient, OperationFailedError, OperationTimeoutError

async def main():
    # Create async client
    client = AsyncPlatoClient(
        base_url="https://api.plato.so",
        headers={"X-API-Key": "your-api-key"}
    )
    
    # Monitor operation with 10 minute timeout
    try:
        await client.monitor_operation_sync("correlation-id-123", timeout_seconds=600)
        print("Operation completed successfully!")
    except OperationTimeoutError:
        print("Operation timed out")
    except OperationFailedError as e:
        print(f"Operation failed: {e}")

asyncio.run(main())
```

## SSE Monitoring Helper Methods

The SDK provides two convenient helper methods for monitoring long-running operations via Server-Sent Events (SSE).

### `monitor_operation_sync`

Monitor an operation synchronously and wait for completion:

```python
import sys
from pathlib import Path

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import PlatoClient

client = PlatoClient(
    base_url="https://api.plato.so",
    headers={"X-API-Key": "your-api-key"}
)

# Simple usage - blocks until operation completes
client.monitor_operation_sync("correlation-id-123", timeout_seconds=600)
```

**Parameters:**
- `correlation_id` (str): Correlation ID from sandbox creation or setup operation
- `timeout_seconds` (float): Maximum time to wait (default: 600 seconds)
- `request_options` (Optional[RequestOptions]): Request-specific configuration

**Raises:**
- `OperationTimeoutError`: If the operation times out
- `OperationFailedError`: If the operation fails

### `monitor_operation_with_events`

Monitor an operation with real-time event callbacks:

```python
import sys
from pathlib import Path

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import PlatoClient
from types import OperationEvent, OperationEventType  # type: ignore

def handle_event(event: OperationEvent):
    if event.type == OperationEventType.PROGRESS:
        print(f"Progress: {event.message}")
    elif event.type == OperationEventType.CONNECTED:
        print("Connected to SSE stream")

client = PlatoClient(
    base_url="https://api.plato.so",
    headers={"X-API-Key": "your-api-key"}
)

# Monitor with event callback
client.monitor_operation_with_events(
    "correlation-id-123",
    callback=handle_event,
    timeout_seconds=600
)
```

**Parameters:**
- `correlation_id` (str): Correlation ID from sandbox creation or setup operation
- `callback` (Callable): Function to call for each event (async for AsyncPlatoClient)
- `timeout_seconds` (float): Maximum time to wait (default: 600 seconds)
- `request_options` (Optional[RequestOptions]): Request-specific configuration

## Complete Example

```python
import sys
from pathlib import Path

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import PlatoClient
from types import (  # type: ignore
    SimConfigDataset, SimConfigCompute, SimConfigMetadata,
    OperationEvent, OperationEventType
)

# Create client
client = PlatoClient(
    base_url="https://api.plato.so",
    headers={"X-API-Key": "your-api-key"}
)

# Create a sandbox
response = client.create_sandbox(
    dataset="base",
    plato_dataset_config=SimConfigDataset(
        compute=SimConfigCompute(
            cpus=2,
            memory=4096,
            disk=20480,
            app_port=8080,
            plato_messaging_port=8081,
        ),
        metadata=SimConfigMetadata(
            name="My Sandbox",
        ),
    ),
)

print(f"Sandbox creation initiated: {response.job_id}")
print(f"Correlation ID: {response.correlation_id}")

# Monitor the creation process
def log_progress(event: OperationEvent):
    if event.type == OperationEventType.PROGRESS:
        print(f"  → {event.message}")

try:
    client.monitor_operation_with_events(
        response.correlation_id,
        callback=log_progress,
        timeout_seconds=600
    )
    print("✓ Sandbox created successfully!")
except Exception as e:
    print(f"✗ Sandbox creation failed: {e}")
```

## Using the Generated SDK Directly

All methods from the generated SDK are available directly:

```python
import sys
from pathlib import Path

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import PlatoClient

client = PlatoClient(
    base_url="https://api.plato.so",
    headers={"X-API-Key": "your-api-key"}
)

# All generated SDK methods work as expected
job_status = client.get_job_status("job-id-123")
sandboxes = client.list_simulators()
```

## Advanced Configuration

```python
import sys
from pathlib import Path
import httpx

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import PlatoClient

# Custom httpx client with advanced configuration
httpx_client = httpx.Client(
    timeout=30.0,
    verify=True,
    http2=True,
)

client = PlatoClient(
    base_url="https://api.plato.so",
    headers={
        "X-API-Key": "your-api-key",
        "User-Agent": "MyApp/1.0",
    },
    timeout=30.0,
    follow_redirects=True,
    httpx_client=httpx_client,
)
```

## Development

When Fern regenerates the SDK at `python-generated/`, your custom helper methods in this package will remain intact.

### Project Structure

```
sdks/
├── python/                 # ← Your permanent code (won't be touched by Fern)
│   ├── __init__.py
│   ├── client.py          # Sync client with helpers
│   ├── async_client.py    # Async client with helpers
│   └── README.md
└── python-generated/      # ← Auto-generated by Fern (can be regenerated)
    ├── client.py          # Base generated client
    └── types/
        └── ...
```

## Error Handling

The helper methods raise specific exceptions:

```python
import sys
from pathlib import Path

# Add python-generated to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-generated"))

from plato import PlatoClient, OperationFailedError, OperationTimeoutError

client = PlatoClient(base_url="https://api.plato.so")

try:
    client.monitor_operation_sync("correlation-id", timeout_seconds=300)
except OperationTimeoutError:
    print("Operation took too long")
except OperationFailedError as e:
    print(f"Operation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## License

MIT

## Support

- Documentation: https://docs.plato.so
- Issues: https://github.com/plato-app/plato-python-sdk/issues
- Email: support@plato.so

