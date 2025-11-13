/**
 * PlatoClient wraps the generated Fern SDK with additional helper methods.
 * 
 * This class provides:
 * - Automatic heartbeat management for environments and VMs
 * - Convenience wrappers that won't be lost during SDK regeneration
 */

import { ApiClient } from './_generated/Client.js';
import type { BaseClientOptions, BaseRequestOptions } from './_generated/BaseClient.js';
import type * as Api from './_generated/api/index.js';
import { OperationEvent, OperationTimeoutError, OperationFailedError } from './types.js';

export interface PlatoClientOptions extends BaseClientOptions {}

export class PlatoClient extends ApiClient {
    private heartbeatTimers: Map<string, NodeJS.Timeout> = new Map();
    private heartbeatJobGroupIds: Map<string, string> = new Map();
    private heartbeatInterval: number = 30000; // 30 seconds

    constructor(options: PlatoClientOptions) {
        super(options);
    }

    /**
     * Start sending periodic heartbeats for an environment.
     * 
     * @param jobGroupId - The job_group_id to send heartbeats to
     * @param jobPublicId - The job_public_id to key the heartbeat by
     * 
     * @example
     * ```typescript
     * const client = new PlatoClient({ baseUrl: 'https://api.plato.so', apiKey: 'key' });
     * client.startHeartbeat('job-group-123', 'job-public-123');
     * ```
     */
    public startHeartbeat(jobGroupId: string, jobPublicId: string): void {
        // Stop existing heartbeat if any
        this.stopHeartbeat(jobPublicId);

        // Store the mapping
        this.heartbeatJobGroupIds.set(jobPublicId, jobGroupId);

        // Start periodic heartbeat
        const timer = setInterval(async () => {
            try {
                await this.env.sendHeartbeatApi({ job_id: jobGroupId });
            } catch (error) {
                console.warn(`Warning: Heartbeat failed for job ${jobPublicId} (group ${jobGroupId}):`, error);
            }
        }, this.heartbeatInterval);

        this.heartbeatTimers.set(jobPublicId, timer);
    }

    /**
     * Stop sending heartbeats for an environment.
     * 
     * @param jobPublicId - The job_public_id to stop heartbeats for
     * 
     * @example
     * ```typescript
     * client.stopHeartbeat('job-public-123');
     * ```
     */
    public stopHeartbeat(jobPublicId: string): void {
        const timer = this.heartbeatTimers.get(jobPublicId);
        if (timer) {
            clearInterval(timer);
            this.heartbeatTimers.delete(jobPublicId);
        }
        this.heartbeatJobGroupIds.delete(jobPublicId);
    }

    /**
     * Stop all active heartbeat timers.
     * Useful for cleanup when shutting down the client.
     * 
     * @example
     * ```typescript
     * client.stopAllHeartbeats();
     * ```
     */
    public stopAllHeartbeats(): void {
        for (const jobPublicId of Array.from(this.heartbeatTimers.keys())) {
            this.stopHeartbeat(jobPublicId);
        }
    }

    /**
     * Create an environment with automatic heartbeat.
     * 
     * Wraps the generated makeEnvApi method and automatically starts
     * heartbeat when autoHeartbeat is true (default).
     * 
     * @param request - Environment creation request
     * @param options - Optional settings including autoHeartbeat flag
     * @returns Promise with environment creation response
     * 
     * @example
     * ```typescript
     * const response = await client.makeEnv({
     *   interface_type: 'browser',
     *   source: 'my-app',
     *   env_id: 'test-env',
     *   env_config: {}
     * }, { autoHeartbeat: true });
     * 
     * // Heartbeat is now running automatically
     * // Stop it when done: client.stopHeartbeat(response.job_public_id)
     * ```
     */
    public async makeEnv(
        request: Api.MakeEnvRequest2,
        options?: {
            autoHeartbeat?: boolean;
            requestOptions?: BaseRequestOptions;
        }
    ): Promise<Api.MakeEnvResponse> {
        const data = await this.env.makeEnvApi(request, options?.requestOptions);

        // Start heartbeat if enabled and we have the necessary IDs
        const autoHeartbeat = options?.autoHeartbeat ?? true;
        if (autoHeartbeat && data.job_public_id && data.job_group_id) {
            this.startHeartbeat(data.job_group_id, data.job_public_id);
        }

        return data;
    }

    /**
     * Create a VM/sandbox with automatic heartbeat.
     * 
     * Wraps the generated createVmApi method and automatically starts
     * heartbeat when autoHeartbeat is true (default).
     * 
     * @param request - VM creation request
     * @param options - Optional settings including autoHeartbeat flag
     * @returns Promise with VM creation response
     * 
     * @example
     * ```typescript
     * const response = await client.createVm({
     *   dataset: 'base',
     *   plato_dataset_config: config
     * }, { autoHeartbeat: true });
     * 
     * // Monitor the operation via SSE
     * // await client.monitorOperation(response.correlation_id);
     * ```
     */
    public async createVm(
        request: Api.CreateVmRequest,
        options?: {
            autoHeartbeat?: boolean;
            requestOptions?: BaseRequestOptions;
        }
    ): Promise<Api.CreateVmResponse> {
        const data = await this.publicBuild.createVmApi(request, options?.requestOptions);

        // Start heartbeat if enabled and we have the necessary IDs
        const autoHeartbeat = options?.autoHeartbeat ?? true;
        if (autoHeartbeat && data.job_public_id && data.job_group_id) {
            this.startHeartbeat(data.job_group_id, data.job_public_id);
        }

        return data;
    }

    /**
     * Close an environment and stop its heartbeat.
     * 
     * Wraps the generated closeEnvApi method and ensures the heartbeat
     * is stopped when the environment is closed.
     * 
     * @param jobGroupId - The job_group_id to close
     * @param requestOptions - Optional request configuration
     * @returns Promise with close environment response
     * 
     * @example
     * ```typescript
     * await client.closeEnv('job-group-123');
     * // Heartbeat is automatically stopped
     * ```
     */
    public async closeEnv(
        jobGroupId: string,
        requestOptions?: BaseRequestOptions
    ): Promise<Api.CloseEnvResponse> {
        const data = await this.env.closeEnvApi({ job_group_id: jobGroupId }, requestOptions);

        // Stop heartbeat if we have it tracked
        for (const [jobPublicId, trackedJobGroupId] of this.heartbeatJobGroupIds.entries()) {
            if (trackedJobGroupId === jobGroupId) {
                this.stopHeartbeat(jobPublicId);
                break;
            }
        }

        return data;
    }

    /**
     * Delete a VM and stop its heartbeat.
     * 
     * Wraps the generated VM deletion and ensures the heartbeat
     * is stopped when the VM is deleted.
     * 
     * @param publicId - The job_public_id to delete
     * @param requestOptions - Optional request configuration
     * @returns Promise with VM management response
     * 
     * @example
     * ```typescript
     * await client.deleteVm('job-public-123');
     * // Heartbeat is automatically stopped
     * ```
     */
    public async deleteVm(
        publicId: string,
        requestOptions?: BaseRequestOptions
    ): Promise<Api.VmManagementResponse> {
        // Stop heartbeat first (keyed by job_public_id which is the public_id)
        this.stopHeartbeat(publicId);

        // Call the generated API
        const data = await this.publicBuild.deleteVmApi({ public_id: publicId }, requestOptions);

        return data;
    }

    /**
     * Parse SSE stream from the operation events endpoint.
     * 
     * Note: This is a helper method since Fern doesn't yet natively support SSE streaming.
     * You can use the raw fetch API to get the SSE stream and parse events.
     * 
     * @param correlationId - Correlation ID from sandbox/VM creation
     * @returns AsyncGenerator of OperationEvent objects
     * 
     * @example
     * ```typescript
     * for await (const event of client.streamOperationEvents('correlation-123')) {
     *   console.log('Event:', event.type, event.message);
     *   if (event.success) break;
     * }
     * ```
     */
    public async *streamOperationEvents(
        correlationId: string
    ): AsyncGenerator<OperationEvent> {
        // Get base URL from options
        const options = (this as any)._options;
        const baseUrl = options.baseUrl || options.environment;
        const url = `${baseUrl}/public-build/events/${encodeURIComponent(correlationId)}`;
        
        const headers: Record<string, string> = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
        };

        // Add API key if available
        if (options.apiKey) {
            headers['X-Api-Key'] = options.apiKey;
        }

        const response = await fetch(url, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            throw new OperationFailedError(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('Response body is not readable');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                
                // Keep the last incomplete line in the buffer
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data.trim()) {
                            try {
                                const event = JSON.parse(data) as OperationEvent;
                                yield event;
                            } catch (error) {
                                console.warn('Failed to parse SSE event:', data, error);
                            }
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * Monitor an operation and wait for completion.
     * 
     * This helper wraps the SSE stream and handles success/failure automatically.
     * 
     * @param correlationId - Correlation ID from operation
     * @param options - Timeout and callback options
     * @returns Promise that resolves on success
     * @throws {OperationTimeoutError} If timeout is exceeded
     * @throws {OperationFailedError} If operation fails
     * 
     * @example
     * ```typescript
     * await client.monitorOperation('correlation-123', {
     *   timeoutSeconds: 600,
     *   onEvent: (event) => console.log('Progress:', event.message)
     * });
     * ```
     */
    public async monitorOperation(
        correlationId: string,
        options?: {
            timeoutSeconds?: number;
            onEvent?: (event: OperationEvent) => void;
        }
    ): Promise<void> {
        const timeoutSeconds = options?.timeoutSeconds ?? 600;
        const startTime = Date.now();

        for await (const event of this.streamOperationEvents(correlationId)) {
            // Check timeout
            const elapsedSeconds = (Date.now() - startTime) / 1000;
            if (elapsedSeconds > timeoutSeconds) {
                throw new OperationTimeoutError(
                    `Operation timed out after ${timeoutSeconds} seconds`
                );
            }

            // Call event callback if provided
            if (options?.onEvent) {
                options.onEvent(event);
            }

            // Handle terminal events
            if (event.type === 'connected') {
                continue;
            }

            if (event.type === 'error') {
                const errorMsg = event.error || event.message || 'Unknown error';
                throw new OperationFailedError(`Operation failed: ${errorMsg}`);
            }

            // Check success field for other events
            if (event.success === true) {
                return; // Operation completed successfully
            } else if (event.success === false) {
                const errorMsg = event.error || event.message || 'Operation failed';
                throw new OperationFailedError(errorMsg);
            }
        }

        throw new OperationFailedError('Stream ended without terminal event');
    }
}
