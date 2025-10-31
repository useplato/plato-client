#!/usr/bin/env python3
"""
Test script for Plato SDK - Creates sandbox from artifact, monitors SSE, 
then creates snapshot and monitors it.
"""

import sys

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


def print_separator():
    """Print a separator line."""
    print("\n" + "=" * 70 + "\n")


def main():
    """Main test function."""
    print_separator()
    print("PLATO SDK TEST - Sandbox Creation & Snapshot Workflow")
    print_separator()
    
    # Get configuration from user input
    base_url = "https://plato.so/api"
    api_key = "5cdd615f-612a-4a5a-bbe0-d0a52fff831d"
    if not api_key:
        print("✗ API key is required. Exiting.")
        return 1
    
    artifact_id = "1cbef69c-7ffa-47a8-9d55-747ba6d78a66"
    dataset = "blank"
    
    # Create client
    print(f"\nInitializing Plato client...")
    print(f"  Base URL: {base_url}")
    print(f"  Dataset: {dataset}")
    if artifact_id:
        print(f"  Artifact ID: {artifact_id}")
    
    client = PlatoClient(
        base_url=base_url,
        headers={"X-API-Key": api_key}
    )
    
    print("  ✓ Client initialized")
    
    # Step 1: Create sandbox (optionally from artifact)
    print_separator()
    print("STEP 1: Creating Sandbox")
    print_separator()
    
    try:
        print("Creating sandbox...")
        
        create_kwargs = {
            "dataset": dataset,
            "service": "espocrm",
        }
        
        # Add artifact_id if provided, otherwise use config
        if artifact_id:
            create_kwargs["artifact_id"] = artifact_id
            print(f"  Creating from artifact: {artifact_id}")
        else:
            # Only provide config when not using artifact_id
            create_kwargs["plato_dataset_config"] = SimConfigDataset(
                compute=SimConfigCompute(
                    cpus=2,
                    memory=4096,
                    disk=8192,
                    app_port=80,
                    plato_messaging_port=7000,
                ),
                metadata=SimConfigMetadata(
                    name="EspoCRM",
                ),
                services={},
                listeners={},
            )
        
        response = client.create_sandbox(**create_kwargs, auto_heartbeat=False)
        
        print(f"\n✓ Sandbox creation initiated:")
        print(f"  Job Public ID: {response.job_public_id}")
        print(f"  Job Group ID: {response.job_group_id}")
        print(f"  Status: {response.status}")
        print(f"  Correlation ID: {response.correlation_id}")
        if response.url:
            print(f"  URL: {response.url}")
        
        job_public_id = response.job_public_id
        job_group_id = response.job_group_id
        correlation_id = response.correlation_id
        
    except Exception as e:
        print(f"\n✗ Failed to create sandbox: {e}")
        return 1
    
    # Step 2: Monitor sandbox creation
    print("\nMonitoring sandbox creation (waiting for completion)...")
    
    try:
        client.monitor_operation_sync(correlation_id, timeout_seconds=600)
        print("✓ Sandbox created successfully!")

        client.start_heartbeat(job_group_id, job_public_id)
        print("✓ Heartbeat started successfully!")
        
    except OperationTimeoutError:
        print("\n✗ Sandbox creation timed out after 10 minutes")
        return 1
        
    except OperationFailedError as e:
        print(f"\n✗ Sandbox creation failed: {e}")
        return 1
    
    # Step 3: Wait for user input
    print_separator()
    print("STEP 2: Sandbox Ready - Waiting for User")
    print_separator()
    
    print(f"Sandbox is now running with Job ID: {job_public_id}")
    print("\nYou can now:")
    print("  - Access the sandbox")
    print("  - Make changes")
    print("  - Test functionality")
    print("\nPress ENTER when you're ready to create a snapshot...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        return 1
    
    # Step 4: Create snapshot
    print_separator()
    print("STEP 3: Creating Snapshot")
    print_separator()
    
    try:
        print(f"Creating snapshot of sandbox {job_public_id}...")
        
        snapshot_response = client.create_snapshot(
            public_id=job_public_id,
            dataset=dataset,
        )
        
        print(f"\n✓ Snapshot creation initiated:")
        print(f"  Artifact ID: {snapshot_response.artifact_id}")
        print(f"  Status: {snapshot_response.status}")
        print(f"  Timestamp: {snapshot_response.timestamp}")
        print(f"  Correlation ID: {snapshot_response.correlation_id}")
        print(f"  S3 URI: {snapshot_response.s_3_uri}")
        if snapshot_response.git_hash:
            print(f"  Git Hash: {snapshot_response.git_hash}")
        
        snapshot_correlation_id = snapshot_response.correlation_id
        
    except Exception as e:
        print(f"\n✗ Failed to create snapshot: {e}")
        return 1
    
    # Step 5: Monitor snapshot creation
    print("\nMonitoring snapshot creation (waiting for completion)...")
    
    try:
        client.monitor_operation_sync(
            snapshot_correlation_id,
            timeout_seconds=600  # 10 minute timeout
        )
        print("✓ Snapshot created successfully!")
        
    except OperationTimeoutError:
        print("\n✗ Snapshot creation timed out after 10 minutes")
        return 1
        
    except OperationFailedError as e:
        print(f"\n✗ Snapshot creation failed: {e}")
        return 1

    # close sandbox
    client.delete_sandbox(job_public_id)
    print(f"✓ Sandbox {job_public_id} deleted successfully!")
    
    # Summary
    print_separator()
    print("SUMMARY")
    print_separator()
    
    print("✓ All operations completed successfully!")
    print(f"\nSandbox Details:")
    print(f"  Job Public ID: {job_public_id}")
    print(f"\nSnapshot Details:")
    print(f"  Artifact ID: {snapshot_response.artifact_id}")
    print(f"  S3 URI: {snapshot_response.s_3_uri}")
    
    print("\nYou can now:")
    print(f"  - Create new sandboxes from this artifact: {snapshot_response.artifact_id}")
    print(f"  - Use it in your workflows")
    
    print_separator()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

