"""
Example demonstrating synchronous SSE monitoring with the Plato SDK.
"""

from plato import (
    PlatoClient,
    OperationFailedError,
    OperationTimeoutError,
)
from plato._generated.types import (
    SimConfigDataset,
    SimConfigCompute,
    SimConfigMetadata,
)


def create_and_monitor_sync():
    """Create a sandbox and monitor its creation synchronously."""
    
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
                name="Example Sandbox",
            ),
        ),
    )
    
    print(f"Sandbox creation initiated:")
    print(f"  Job ID: {response.job_id}")
    print(f"  Correlation ID: {response.correlation_id}")
    print("\nMonitoring operation (this will block until complete)...")
    
    # Monitor synchronously - blocks until completion
    try:
        client.monitor_operation_sync(
            response.correlation_id,
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
    print("Plato SDK - Synchronous SSE Monitoring Example")
    print("=" * 60)
    print()
    
    success = create_and_monitor_sync()
    
    print()
    print("=" * 60)
    if success:
        print("Example completed successfully!")
    else:
        print("Example failed - see errors above")
    print("=" * 60)


if __name__ == "__main__":
    main()

