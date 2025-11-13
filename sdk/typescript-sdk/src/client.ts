/**
 * PlatoClient - Enhanced wrapper around the generated OpenAPI SDK
 * 
 * Features:
 * - Automatic heartbeat management for environments and VMs
 * - SSE stream monitoring with timeout and error handling
 * - Maintains backward compatibility with the base SDK
 */

import {
    Configuration,
    EnvApi,
    PublicBuildApi,
    GiteaApi,
    SimulatorApi,
} from './index';

import type {
    MakeEnvRequest2,
    MakeEnvResponse,
    CreateVMRequest,
    CreateVMResponse,
    GetOperationEventsApiPublicBuildEventsCorrelationIdGet200Response,
} from './models/index';

export interface PlatoClientOptions {
    apiKey: string;
    basePath?: string;
    heartbeatInterval?: number; // milliseconds, default 30000
}

export interface OperationEvent {
    type: string;
    success?: boolean;
    message?: string;
    error?: string;
}

export class OperationTimeoutError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'OperationTimeoutError';
    }
}

export class OperationFailedError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'OperationFailedError';
    }
}

/**
 * PlatoClient wraps the generated SDK with additional helper methods.
 */
export class PlatoClient {
    public readonly env: EnvApi;
    public readonly publicBuild: PublicBuildApi;
    public readonly gitea: GiteaApi;
    public readonly simulator: SimulatorApi;

    private readonly config: Configuration;
    private readonly heartbeatTimers: Map<string, NodeJS.Timeout> = new Map();
    private readonly heartbeatJobGroupIds: Map<string, string> = new Map();
    private readonly heartbeatInterval: number;

    constructor(options: PlatoClientOptions) {
        this.heartbeatInterval = options.heartbeatInterval || 30000;

        // Create configuration with API key authentication
        this.config = new Configuration({
            basePath: options.basePath || 'http://localhost',
            headers: {
                'X-Api-Key': options.apiKey,
            },
        });

        // Initialize API clients
        this.env = new EnvApi(this.config);
        this.publicBuild = new PublicBuildApi(this.config);
        this.gitea = new GiteaApi(this.config);
        this.simulator = new SimulatorApi(this.config);
    }

    /**
     * Create an environment with automatic heartbeat management.
     */
    async makeEnvironment(request: MakeEnvRequest2): Promise<MakeEnvResponse> {
        const response = await this.env.makeEnvApiEnvMake2Post({ makeEnvRequest2: request });
        
        // Start heartbeat using the job ID
        if (response.jobId) {
            this.startHeartbeat(response.jobId, response.jobId);
        }

        return response;
    }

    /**
     * Create a sandbox VM with automatic heartbeat management.
     */
    async createSandbox(request: CreateVMRequest): Promise<CreateVMResponse> {
        const response = await this.publicBuild.createVmApiPublicBuildVmCreatePost({ createVMRequest: request });
        
        // Extract correlation_id for heartbeat
        if (response.correlationId) {
            this.startHeartbeat(response.correlationId, response.correlationId);
        }

        return response;
    }

    /**
     * Wait for an environment to be ready.
     * 
     * @param jobGroupId - The job group ID to wait for
     * @param pollIntervalMs - How often to check status (default: 2000ms)
     * @param timeoutMs - Maximum time to wait (default: 300000ms = 5 minutes)
     * @returns Promise that resolves when environment is ready
     */
    async waitForEnvironmentReady(
        jobGroupId: string,
        pollIntervalMs: number = 2000,
        timeoutMs: number = 300000
    ): Promise<void> {
        const startTime = Date.now();
        
        while (true) {
            const status = await this.env.getJobStatusApiEnvJobGroupIdStatusGet({ jobGroupId });
            
            if (status.status === 'ready') {
                return;
            }
            
            if (status.status === 'failed' || status.status === 'error') {
                throw new OperationFailedError(`Environment failed with status: ${status.status}`);
            }
            
            if (Date.now() - startTime > timeoutMs) {
                throw new OperationTimeoutError(`Environment not ready after ${timeoutMs}ms`);
            }
            
            await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
        }
    }

    /**
     * Close an environment and stop its heartbeat.
     */
    async closeEnvironment(jobGroupId: string): Promise<any> {
        this.stopHeartbeat(jobGroupId);
        return await this.env.closeEnvApiEnvJobGroupIdClosePost({ jobGroupId });
    }

    /**
     * Delete a VM and stop its heartbeat.
     */
    async closeVM(publicId: string): Promise<any> {
        this.stopHeartbeat(publicId);
        return await this.publicBuild.closeVmApiPublicBuildVmPublicIdDelete({ publicId });
    }

    /**
     * Monitor an operation via SSE stream until completion.
     * 
     * @param correlationId - The correlation ID for the operation
     * @param timeoutMs - Timeout in milliseconds (default: 300000 = 5 minutes)
     * @returns Promise that resolves when operation succeeds or rejects on failure/timeout
     */
    async monitorOperationSync(correlationId: string, timeoutMs: number = 300000): Promise<OperationEvent> {
        return new Promise(async (resolve, reject) => {
            const timeoutId = setTimeout(() => {
                reject(new OperationTimeoutError(`Operation timed out after ${timeoutMs}ms`));
            }, timeoutMs);

            try {
                // Note: The generated SDK doesn't have native SSE support,
                // so we'll need to use fetch directly
                const response = await fetch(
                    `${this.config.basePath}/public-build/events/${correlationId}`,
                    {
                        headers: {
                            'X-Api-Key': this.config.headers?.['X-Api-Key'] as string,
                            'Accept': 'text/event-stream',
                        },
                    }
                );

                if (!response.ok) {
                    clearTimeout(timeoutId);
                    reject(new OperationFailedError(`HTTP ${response.status}: ${response.statusText}`));
                    return;
                }

                const reader = response.body?.getReader();
                const decoder = new TextDecoder();

                if (!reader) {
                    clearTimeout(timeoutId);
                    reject(new OperationFailedError('No response body'));
                    return;
                }

                // Read SSE stream
                while (true) {
                    const { done, value } = await reader.read();
                    
                    if (done) {
                        clearTimeout(timeoutId);
                        reject(new OperationFailedError('Stream ended without completion'));
                        break;
                    }

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const event: OperationEvent = JSON.parse(line.slice(6));
                                
                                // Check for completion
                                if (event.type === 'complete') {
                                    clearTimeout(timeoutId);
                                    if (event.success) {
                                        resolve(event);
                                    } else {
                                        reject(new OperationFailedError(event.message || 'Operation failed'));
                                    }
                                    return;
                                }

                                // Check for error
                                if (event.type === 'error') {
                                    clearTimeout(timeoutId);
                                    reject(new OperationFailedError(event.error || event.message || 'Unknown error'));
                                    return;
                                }
                            } catch (parseError) {
                                // Ignore parse errors for individual events
                                console.warn('Failed to parse SSE event:', line);
                            }
                        }
                    }
                }
            } catch (error) {
                clearTimeout(timeoutId);
                reject(error);
            }
        });
    }

    /**
     * Start sending heartbeats for a job.
     */
    private startHeartbeat(timerId: string, jobGroupId: string): void {
        // Stop existing heartbeat if any
        this.stopHeartbeat(timerId);

        // Store job group ID for heartbeat calls
        this.heartbeatJobGroupIds.set(timerId, jobGroupId);

        // Start new heartbeat interval
        const timer = setInterval(async () => {
            try {
                await this.env.sendHeartbeatApiEnvJobIdHeartbeatPost({ jobId: jobGroupId });
            } catch (error) {
                console.error(`Heartbeat failed for ${jobGroupId}:`, error);
            }
        }, this.heartbeatInterval);

        this.heartbeatTimers.set(timerId, timer);
    }

    /**
     * Stop sending heartbeats for a job.
     */
    private stopHeartbeat(timerId: string): void {
        const timer = this.heartbeatTimers.get(timerId);
        if (timer) {
            clearInterval(timer);
            this.heartbeatTimers.delete(timerId);
            this.heartbeatJobGroupIds.delete(timerId);
        }
    }

    /**
     * Stop all active heartbeats (useful for cleanup).
     */
    stopAllHeartbeats(): void {
        for (const timer of this.heartbeatTimers.values()) {
            clearInterval(timer);
        }
        this.heartbeatTimers.clear();
        this.heartbeatJobGroupIds.clear();
    }

    /**
     * Cleanup method to stop all heartbeats before destroying the client.
     */
    destroy(): void {
        this.stopAllHeartbeats();
    }
}

