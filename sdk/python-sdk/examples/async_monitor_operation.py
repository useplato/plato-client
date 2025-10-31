"""
Example demonstrating async SSE monitoring with the Plato SDK.
"""

import asyncio

from plato import (
    AsyncPlatoClient,
    OperationFailedError,
    OperationTimeoutError,
    OperationEvent,
    OperationEventType,
)
from plato._generated.types import (
    SimConfigDataset,
    SimConfigCompute,
    SimConfigMetadata,
)


async def create_and_monitor_async():
    """Create a sandbox and monitor its creation asynchronously."""
    
    # Create async client
    client = AsyncPlatoClient(
        base_url="https://api.plato.so",
        headers={"X-API-Key": "your-api-key"}
    )
    
    print("Creating sandbox (async)...")
    
    # Create sandbox
    response = await client.create_sandbox(
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
                name="Example Async Sandbox",
            ),
        ),
    )
    
    print(f"Sandbox creation initiated:")
    print(f"  Job ID: {response.job_id}")
    print(f"  Correlation ID: {response.correlation_id}")
    print("\nMonitoring operation asynchronously...")
    
    # Monitor asynchronously
    try:
        await client.monitor_operation_sync(
            response.correlation_id,
            timeout_seconds=600  # 10 minute timeout
        )
        print("\n✓ Sandbox created successfully!")
        print(f"  Job ID: {response.job_id}")
        return True
        
    except OperationTimeoutError:
        print("\n✗ Operation timed out after 10 minutes")
        return False
        
    except OperationFailedError as e:
        print(f"\n✗ Operation failed: {e}")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


async def create_and_monitor_with_async_events():
    """Create a sandbox and monitor with async event callbacks."""
    
    # Create async client
    client = AsyncPlatoClient(
        base_url="https://api.plato.so",
        headers={"X-API-Key": "your-api-key"}
    )
    
    print("\n" + "=" * 60)
    print("Creating sandbox with async event callbacks...")
    print("=" * 60 + "\n")
    
    # Create sandbox
    response = await client.create_sandbox(
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
                name="Example Async Sandbox with Events",
            ),
        ),
    )
    
    print(f"Sandbox creation initiated:")
    print(f"  Job ID: {response.job_id}")
    print(f"  Correlation ID: {response.correlation_id}")
    print()
    
    # Async event callback function
    async def handle_event(event: OperationEvent):
        """Handle each SSE event as it arrives (async)."""
        if event.type == OperationEventType.CONNECTED:
            print("  → Connected to SSE stream")
        elif event.type == OperationEventType.PROGRESS:
            print(f"  → Progress: {event.message}")
            # Could do async operations here, like logging to database
            await asyncio.sleep(0.01)  # Simulate async work
        elif event.type in (OperationEventType.RUN_RESULT, OperationEventType.SSH_RESULT):
            if event.success:
                print(f"  → Completed: {event.type}")
            else:
                print(f"  → Failed: {event.error or event.message}")
        elif event.type == OperationEventType.ERROR:
            print(f"  → Error: {event.error or event.message}")
    
    # Monitor with async event callbacks
    try:
        await client.monitor_operation_with_events(
            response.correlation_id,
            callback=handle_event,
            timeout_seconds=600
        )
        print("\n✓ Sandbox created successfully!")
        return True
        
    except OperationFailedError as e:
        print(f"\n✗ Operation failed: {e}")
        return False


async def main():
    """Run the async examples."""
    print("=" * 60)
    print("Plato SDK - Async SSE Monitoring Examples")
    print("=" * 60)
    print()
    
    # Example 1: Simple async monitoring
    success1 = await create_and_monitor_async()
    
    # Example 2: Async monitoring with event callbacks
    success2 = await create_and_monitor_with_async_events()
    
    print()
    print("=" * 60)
    if success1 and success2:
        print("All async examples completed successfully!")
    else:
        print("Some examples failed - see errors above")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

