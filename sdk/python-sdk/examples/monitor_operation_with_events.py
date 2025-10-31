"""
Example demonstrating SSE monitoring with event callbacks.
"""

from plato import (
    PlatoClient,
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


def create_and_monitor_with_events():
    """Create a sandbox and monitor its creation with event callbacks."""
    
    # Create client
    client = PlatoClient(
        base_url="https://api.plato.so",
        headers={"X-API-Key": "your-api-key"}
    )
    
    print("Creating sandbox...")
    
    # Create sandbox
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
                name="Example Sandbox with Events",
            ),
        ),
    )
    
    print(f"Sandbox creation initiated:")
    print(f"  Job ID: {response.job_id}")
    print(f"  Correlation ID: {response.correlation_id}")
    print("\nMonitoring operation with event callbacks...")
    print()
    
    # Event callback function
    def handle_event(event: OperationEvent):
        """Handle each SSE event as it arrives."""
        if event.type == OperationEventType.CONNECTED:
            print("  → Connected to SSE stream")
        elif event.type == OperationEventType.PROGRESS:
            print(f"  → Progress: {event.message}")
        elif event.type in (OperationEventType.RUN_RESULT, OperationEventType.SSH_RESULT):
            if event.success:
                print(f"  → Completed: {event.type}")
            else:
                print(f"  → Failed: {event.error or event.message}")
        elif event.type == OperationEventType.ERROR:
            print(f"  → Error: {event.error or event.message}")
    
    # Monitor with event callbacks
    try:
        client.monitor_operation_with_events(
            response.correlation_id,
            callback=handle_event,
            timeout_seconds=600  # 10 minute timeout
        )
        print("\n✓ Sandbox created successfully!")
        print(f"  Job ID: {response.job_id}")
        
    except OperationTimeoutError:
        print("\n✗ Operation timed out after 10 minutes")
        return False
        
    except OperationFailedError as e:
        print(f"\n✗ Operation failed: {e}")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False
    
    return True


def main():
    """Run the example."""
    print("=" * 60)
    print("Plato SDK - SSE Monitoring with Events Example")
    print("=" * 60)
    print()
    
    success = create_and_monitor_with_events()
    
    print()
    print("=" * 60)
    if success:
        print("Example completed successfully!")
    else:
        print("Example failed - see errors above")
    print("=" * 60)


if __name__ == "__main__":
    main()

