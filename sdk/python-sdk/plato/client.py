"""
PlatoClient wraps the generated Fern SDK with additional helper methods.
"""

import threading
import time
import typing

from ._generated.client import Api as GeneratedClient
from ._generated.types import (
    OperationEvent, 
    CreateSandboxResponse, 
    DeleteSandboxResponse,
    SimConfigDataset,
    SimConfigCompute,
    SimConfigMetadata
)
from ._generated.core.request_options import RequestOptions


class OperationTimeoutError(Exception):
    """Raised when an operation times out"""
    pass


class OperationFailedError(Exception):
    """Raised when an operation fails"""
    pass


class PlatoClient(GeneratedClient):
    """
    Plato SDK client with additional helper methods for SSE monitoring.
    
    This class wraps the auto-generated Fern SDK and provides convenient
    helper methods that won't be lost during SDK regeneration.
    
    All methods from the generated SDK are available through inheritance.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the client and heartbeat tracking."""
        super().__init__(*args, **kwargs)
        self._heartbeat_threads: typing.Dict[str, threading.Thread] = {}
        self._heartbeat_stop_events: typing.Dict[str, threading.Event] = {}
        self._heartbeat_job_group_ids: typing.Dict[str, str] = {}  # Maps job_public_id -> job_group_id
        self._heartbeat_interval: float = 30.0  # Send heartbeat every 30 seconds

    def monitor_operation_sync(
        self,
        correlation_id: str,
        timeout_seconds: float = 600.0,
        *,
        request_options: typing.Optional[RequestOptions] = None,
    ) -> None:
        """
        Monitor an SSE stream for operation completion and return when done.
        
        This is a synchronous wrapper around monitor_operation that handles
        the stream internally and blocks until the operation completes.
        
        Args:
            correlation_id: Correlation ID from sandbox creation or setup operation
            timeout_seconds: Maximum time to wait for operation completion (default: 600s)
            request_options: Request-specific configuration
            
        Returns:
            None on successful completion
            
        Raises:
            OperationTimeoutError: If the operation times out
            OperationFailedError: If the operation fails or encounters an error
            
        The function automatically handles:
        - "connected" events: continues listening
        - "error" events: raises OperationFailedError immediately
        - "run_result", "ssh_result", or other completion events: checks success field
          and returns (success=True) or raises OperationFailedError (success=False)
          
        Example:
            ```python
            from plato import PlatoClient
            
            client = PlatoClient(base_url="https://api.plato.so")
            
            # Monitor operation with 10 minute timeout
            try:
                client.monitor_operation_sync("correlation-id-123", timeout_seconds=600)
                print("Operation completed successfully!")
            except OperationTimeoutError:
                print("Operation timed out")
            except OperationFailedError as e:
                print(f"Operation failed: {e}")
            ```
        """
        start_time = time.time()
        
        for event in self.monitor_operation(correlation_id, request_options=request_options):
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                raise OperationTimeoutError(
                    f"Operation timed out after {timeout_seconds} seconds"
                )
            
            # Handle different event types
            if event.type == "connected":
                print(f"Connected to SSE stream, event: {event}")
                # Connection established, continue listening
                continue
                
            elif event.type == "error":
                print(f"Error event: {event}")
                # Operation failed
                error_msg = event.error or event.message or "Unknown error"
                raise OperationFailedError(f"Operation failed: {error_msg}")
                
            else:
                print(f"Other event: {event}")
                # Handle all other event types by checking success field
                if event.success:
                    # Operation completed successfully
                    return
                else:
                    # Operation failed
                    error_msg = event.error or event.message or "Operation failed"
                    raise OperationFailedError(error_msg)
            
        # If we exit the loop without a terminal event, that's unexpected
        raise OperationFailedError("Stream ended without terminal event")

    def monitor_operation_with_events(
        self,
        correlation_id: str,
        callback: typing.Callable[[OperationEvent], None],
        timeout_seconds: float = 600.0,
        *,
        request_options: typing.Optional[RequestOptions] = None,
    ) -> None:
        """
        Monitor an SSE stream and invoke a callback for each event.
        
        This method allows you to receive real-time updates about the operation
        progress while handling terminal events (success/failure) automatically.
        
        Args:
            correlation_id: Correlation ID from sandbox creation or setup operation
            callback: Function to call for each event received
            timeout_seconds: Maximum time to wait for operation completion (default: 600s)
            request_options: Request-specific configuration
            
        Returns:
            None on successful completion
            
        Raises:
            OperationTimeoutError: If the operation times out
            OperationFailedError: If the operation fails or encounters an error
            
        Example:
            ```python
            from plato import PlatoClient, OperationEvent
            
            def handle_event(event: OperationEvent):
                if event.type == "progress":
                    print(f"Progress: {event.message}")
                elif event.type == "connected":
                    print("Connected to SSE stream")
            
            client = PlatoClient(base_url="https://api.plato.so")
            
            try:
                client.monitor_operation_with_events(
                    "correlation-id-123",
                    callback=handle_event,
                    timeout_seconds=600
                )
                print("Operation completed successfully!")
            except OperationFailedError as e:
                print(f"Operation failed: {e}")
            ```
        """
        start_time = time.time()
        
        for event in self.monitor_operation(correlation_id, request_options=request_options):
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                raise OperationTimeoutError(
                    f"Operation timed out after {timeout_seconds} seconds"
                )
            
            # Invoke callback for every event
            callback(event)
            
            # Handle terminal events
            if event.type == "error":
                # Operation failed
                error_msg = event.error or event.message or "Unknown error"
                raise OperationFailedError(f"Operation failed: {error_msg}")
                
            elif event.type != "connected":
                # Handle all other event types by checking success field
                if event.success:
                    # Operation completed successfully
                    return
                else:
                    # Operation failed
                    error_msg = event.error or event.message or "Operation failed"
                    raise OperationFailedError(error_msg)
                    
        # If we exit the loop without a terminal event, that's unexpected
        raise OperationFailedError("Stream ended without terminal event")
    
    def _heartbeat_worker(self, job_public_id: str) -> None:
        """
        Background worker that sends periodic heartbeats for a sandbox.
        
        Args:
            job_public_id: The job_public_id (used to look up job_group_id)
        """
        stop_event = self._heartbeat_stop_events.get(job_public_id)
        job_group_id = self._heartbeat_job_group_ids.get(job_public_id)
        
        if not stop_event or not job_group_id:
            return
            
        while not stop_event.is_set():
            try:
                # Send heartbeat to job_group_id
                self.send_heartbeat(job_group_id)
            except Exception as e:
                # Log error but continue - heartbeat failures shouldn't crash the thread
                print(f"Warning: Heartbeat failed for job {job_public_id} (group {job_group_id}): {e}")
            
            # Wait for interval or until stop event is set
            stop_event.wait(self._heartbeat_interval)
    
    def start_heartbeat(self, job_group_id: str, job_public_id: str) -> None:
        """
        Start sending periodic heartbeats for a sandbox.
        
        Heartbeats are sent to job_group_id but keyed/tracked by job_public_id.
        
        Args:
            job_group_id: The job_group_id to send heartbeats to
            job_public_id: The job_public_id to key the heartbeat by
            
        Example:
            ```python
            client = PlatoClient(base_url="https://api.plato.so")
            client.start_heartbeat("job-group-123", "job-public-123")
            ```
        """
        # Stop existing heartbeat if any
        self.stop_heartbeat(job_public_id)
        
        # Store the job_group_id mapping
        self._heartbeat_job_group_ids[job_public_id] = job_group_id
        
        # Create stop event
        stop_event = threading.Event()
        self._heartbeat_stop_events[job_public_id] = stop_event
        
        # Start heartbeat thread
        thread = threading.Thread(
            target=self._heartbeat_worker,
            args=(job_public_id,),
            daemon=True,
            name=f"heartbeat-{job_public_id}"
        )
        self._heartbeat_threads[job_public_id] = thread
        thread.start()
    
    def stop_heartbeat(self, job_public_id: str) -> None:
        """
        Stop sending heartbeats for a sandbox.
        
        Args:
            job_public_id: The job_public_id to stop heartbeats for
            
        Example:
            ```python
            client = PlatoClient(base_url="https://api.plato.so")
            client.stop_heartbeat("job-public-123")
            ```
        """
        # Signal thread to stop
        if job_public_id in self._heartbeat_stop_events:
            self._heartbeat_stop_events[job_public_id].set()
        
        # Wait for thread to finish
        if job_public_id in self._heartbeat_threads:
            thread = self._heartbeat_threads[job_public_id]
            if thread.is_alive():
                thread.join(timeout=1.0)
            del self._heartbeat_threads[job_public_id]
        
        # Clean up stop event
        if job_public_id in self._heartbeat_stop_events:
            del self._heartbeat_stop_events[job_public_id]
        
        # Clean up job_group_id mapping
        if job_public_id in self._heartbeat_job_group_ids:
            del self._heartbeat_job_group_ids[job_public_id]
    
    def stop_all_heartbeats(self) -> None:
        """
        Stop all active heartbeat threads.
        
        Useful for cleanup when shutting down the client.
        
        Example:
            ```python
            client = PlatoClient(base_url="https://api.plato.so")
            # ... use client ...
            client.stop_all_heartbeats()
            ```
        """
        job_public_ids = list(self._heartbeat_threads.keys())
        for job_public_id in job_public_ids:
            self.stop_heartbeat(job_public_id)
    
    def create_sandbox(
        self,
        *,
        dataset: str,
        plato_dataset_config: typing.Optional[SimConfigDataset] = None,
        timeout: typing.Optional[int] = None,
        wait_time: typing.Optional[int] = None,
        alias: typing.Optional[str] = None,
        artifact_id: typing.Optional[str] = None,
        service: typing.Optional[str] = None,
        auto_heartbeat: bool = True,
        request_options: typing.Optional[RequestOptions] = None,
    ) -> CreateSandboxResponse:
        """
        Create a sandbox and automatically start heartbeat.
        
        This method wraps the generated create_sandbox method and adds automatic
        heartbeat functionality when auto_heartbeat=True (default).
        
        You can create a sandbox in two ways:
        1. From a configuration: Provide plato_dataset_config with full VM configuration
        2. From an artifact: Provide artifact_id to launch from a snapshot
        
        Args:
            dataset: Dataset name (e.g., "base")
            plato_dataset_config: Dataset configuration (optional if artifact_id is provided)
            timeout: Timeout in seconds for sandbox creation
            wait_time: Wait time in seconds
            alias: Human-readable alias for the sandbox
            artifact_id: Optional artifact ID to create sandbox from snapshot
            service: Service name
            auto_heartbeat: Whether to automatically start heartbeat (default: True)
            request_options: Request-specific configuration
            
        Returns:
            CreateSandboxResponse with sandbox details
            
        Raises:
            ValueError: If neither plato_dataset_config nor artifact_id is provided
            
        Examples:
            ```python
            # Create from configuration
            client = PlatoClient(base_url="https://api.plato.so")
            response = client.create_sandbox(
                dataset="base",
                plato_dataset_config=config,
                auto_heartbeat=True  # Heartbeat starts automatically
            )
            
            # Create from artifact (config is optional)
            response = client.create_sandbox(
                dataset="base",
                artifact_id="art_123456",
                auto_heartbeat=True
            )
            # Heartbeat is now running in the background
            # Stop it when done: client.stop_heartbeat(response.job_public_id)
            ```
        """
        # Validation: Must provide either config or artifact_id
        if plato_dataset_config is None and artifact_id is None:
            raise ValueError(
                "Must provide either 'plato_dataset_config' or 'artifact_id'. "
                "Use 'plato_dataset_config' to create a new sandbox from configuration, "
                "or 'artifact_id' to create from an existing snapshot."
            )
        
        # If artifact_id is provided but no config, use a default boilerplate config
        # TODO(API): The API should fetch the proper config from the artifact metadata
        # instead of requiring the client to send a boilerplate config
        if plato_dataset_config is None and artifact_id is not None:
            # Default boilerplate config - actual config should be fetched from artifact on API side
            plato_dataset_config = SimConfigDataset(
                compute=SimConfigCompute(
                    cpus=1,
                    memory=512,
                    disk=10240,
                    app_port=8080,
                    plato_messaging_port=7000
                ),
                metadata=SimConfigMetadata(
                    name="Default"
                ),
                services={},
                listeners={}
            )
        
        # Call parent implementation
        response = super().create_sandbox(
            dataset=dataset,
            plato_dataset_config=plato_dataset_config,
            timeout=timeout,
            wait_time=wait_time,
            alias=alias,
            artifact_id=artifact_id,
            service=service,
            request_options=request_options,
        )
        
        # Start heartbeat if enabled
        if auto_heartbeat and response.job_public_id and response.job_group_id:
            self.start_heartbeat(response.job_group_id, response.job_public_id)
        
        return response
    
    def delete_sandbox(
        self, 
        public_id: str, 
        *, 
        request_options: typing.Optional[RequestOptions] = None
    ) -> DeleteSandboxResponse:
        """
        Delete a sandbox and automatically stop its heartbeat.
        
        This method wraps the generated delete_sandbox method and ensures
        the heartbeat is stopped when the sandbox is deleted.
        
        Args:
            public_id: The job_public_id to delete the sandbox for
            request_options: Request-specific configuration
            
        Returns:
            DeleteSandboxResponse
            
        Example:
            ```python
            client = PlatoClient(base_url="https://api.plato.so")
            response = client.delete_sandbox("job-123")
            # Heartbeat is automatically stopped
            ```
        """
        # Stop heartbeat first if it exists (keyed by job_public_id)
        if public_id in self._heartbeat_threads:
            self.stop_heartbeat(public_id)
        
        # Call parent implementation to actually delete the sandbox
        response = super().delete_sandbox(public_id, request_options=request_options)
        
        return response
