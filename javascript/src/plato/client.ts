import axios, { AxiosInstance } from 'axios';
import { PlatoClientError } from './exceptions';
import { z } from 'zod';

export const PlatoTaskSchema = z.object({
  name: z.string(),
  prompt: z.string(),
  start_url: z.string(),
});

export type PlatoTask = z.infer<typeof PlatoTaskSchema>;

// Worker ready response interface
export interface WorkerReadyResponse {
  ready: boolean;
  worker_public_ip?: string;
  worker_ip?: string;
  worker_port?: number;
  health_status?: Record<string, any>;
  error?: string;
}

export class PlatoEnvironment {
  private client: Plato;
  public id: string;
  public alias: string | null = null;
  public fast: boolean = false;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private heartbeatIntervalMs: number = 30000; // 30 seconds
  private runSessionId: string | null = null;

  constructor(client: Plato, id: string, alias?: string, fast: boolean = false) {
    this.client = client;
    this.id = id;
    this.alias = alias || null;
    this.fast = fast;
    this.startHeartbeat();
  }

  async getStatus() {
    return this.client.getJobStatus(this.id);
  }

  async getCdpUrl() {
    return this.client.getCdpUrl(this.id);
  }

  async close() {
    this.stopHeartbeat();
    this.runSessionId = null;
    return this.client.closeEnvironment(this.id);
  }

  async evaluate(value?: any) {
    if (!this.runSessionId) {
      throw new PlatoClientError('No run session ID found');
    }
    return this.client.evaluate(this.runSessionId, value);
  }

  /**
   * Resets the environment with a new task
   * @param task The task to run in the environment, or a simplified object with just name, prompt, and start_url
   * @param testCasePublicId The public ID of the test case
   * @param loadAuthenticated Whether to load authenticated browser state
   * @param userId Optional user ID to associate with the reset
   * @returns The response from the server
   */
  async reset(
    task?: PlatoTask | { name: string; prompt: string; start_url: string },
    testCasePublicId?: string,
    loadAuthenticated: boolean = false,
    userId?: number
  ) {
    try {
      const result = await this.client.resetEnvironment(this.id, task, testCasePublicId, loadAuthenticated, userId);
      // Ensure heartbeat is running after reset
      this.startHeartbeat();
      this.runSessionId = result?.data?.run_session_id || result?.run_session_id;
      return this.runSessionId;
    } catch (error) {
      throw new PlatoClientError('Failed to reset environment: ' + error);
    }
  }

  async getState() {
    return this.client.getEnvironmentState(this.id);
  }

  async getLiveViewUrl() {
    return this.client.getLiveViewUrl(this.id);
  }

  async backup() {
    return this.client.backupEnvironment(this.id);
  }

  /**
   * Starts the heartbeat interval to keep the environment alive
   * @private
   */
  private startHeartbeat() {
    if (this.heartbeatInterval) {
      return; // Already running
    }

    this.heartbeatInterval = setInterval(async () => {
      try {
        await this.client.sendHeartbeat(this.id);
      } catch (error) {
        console.error('Failed to send heartbeat:', error);
      }
    }, this.heartbeatIntervalMs);

    // Make the interval not prevent Node.js from exiting
    if (this.heartbeatInterval.unref) {
      this.heartbeatInterval.unref();
    }
  }

  /**
   * Stops the heartbeat interval
   * @private
   */
  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }


  async waitForReady(timeout?: number): Promise<void> {
    const startTime = Date.now();
    let baseDelay = 500; // Starting delay in milliseconds
    const maxDelay = 8000; // Maximum delay between retries

    // Wait for the job to be running
    let currentDelay = baseDelay;
    while (true) {
      const status = await this.client.getJobStatus(this.id);
      if (status.status.toLowerCase() === 'running') {
        break;
      }

      // Add jitter (±25% of current delay)
      const jitter = (Math.random() - 0.5) * 0.5 * currentDelay;
      await new Promise(resolve => setTimeout(resolve, currentDelay + jitter));

      if (timeout && Date.now() - startTime > timeout) {
        throw new PlatoClientError('Environment failed to start - job never entered running state');
      }

      // Exponential backoff
      currentDelay = Math.min(currentDelay * 2, maxDelay);
    }

    // Wait for the worker to be ready and healthy
    currentDelay = baseDelay; // Reset delay for worker health check
    while (true) {
      const workerStatus: WorkerReadyResponse = await this.client.getWorkerReady(this.id);
      if (workerStatus.ready) {
        break;
      }

      // Add jitter (±25% of current delay)
      const jitter = (Math.random() - 0.5) * 0.5 * currentDelay;
      await new Promise(resolve => setTimeout(resolve, currentDelay + jitter));

      if (timeout && Date.now() - startTime > timeout) {
        const errorMsg = workerStatus.error || 'Unknown error';
        throw new PlatoClientError(`Environment failed to start - worker not ready: ${errorMsg}`);
      }

      // Exponential backoff
      currentDelay = Math.min(currentDelay * 2, maxDelay);
    }
  }

  /**
   * Get the public URL for accessing this environment.
   *
   * @returns The public URL for this environment based on the deployment environment.
   *          Uses alias if available, otherwise uses environment ID.
   *          - Dev: https://{alias|env.id}.dev.sims.plato.so
   *          - Staging: https://{alias|env.id}.staging.sims.plato.so
   *          - Production: https://{alias|env.id}.sims.plato.so
   *          - Local: http://localhost:8081/{alias|env.id}
   * @throws PlatoClientError If unable to determine the environment type.
   */
  getPublicUrl(): string {
    try {
      // Use alias if available, otherwise use environment ID
      const identifier = this.alias || this.id;

      // Determine environment based on base_url
      if (this.client.baseUrl.includes('localhost:8080')) {
        return `http://localhost:8081/${identifier}`;
      } else if (this.client.baseUrl.includes('dev.plato.so')) {
        return `https://${identifier}.dev.sims.plato.so`;
      } else if (this.client.baseUrl.includes('staging.plato.so')) {
        return `https://${identifier}.staging.sims.plato.so`;
      } else if (this.client.baseUrl.includes('plato.so') && !this.client.baseUrl.includes('staging') && !this.client.baseUrl.includes('dev')) {
        return `https://${identifier}.sims.plato.so`;
      } else {
        throw new PlatoClientError('Unknown base URL');
      }
    } catch (error) {
      throw new PlatoClientError(String(error));
    }
  }
}

export class Plato {
  private apiKey: string;
  public baseUrl: string;
  private http: AxiosInstance;

  constructor(apiKey: string, baseUrl?: string) {
    if (!apiKey) {
      throw new PlatoClientError('API key is required');
    }

    this.apiKey = apiKey;
    this.baseUrl = baseUrl || 'https://plato.so/api';

    this.http = axios.create({
      baseURL: this.baseUrl,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Create a new Plato environment for the given environment ID.
   *
   * @param envId The environment ID to create
   * @param openPageOnStart Whether to open the page on start
   * @param recordActions Whether to record actions
   * @param keepalive If true, jobs will not be killed due to heartbeat failures
   * @param alias Optional alias for the job group
   * @param fast Fast mode flag
   * @param artifactId Optional artifact ID to use for the environment
   * @returns The created environment instance
   * @throws PlatoClientError If the API request fails
   */
  async makeEnvironment(
    envId: string,
    openPageOnStart: boolean = false,
    recordActions: boolean = false,
    keepalive: boolean = false,
    alias?: string,
    fast: boolean = false,
    artifactId?: string,
    interfaceType?: "browser" | "noop"
  ): Promise<PlatoEnvironment> {
    if (fast) {
      console.log('Running in fast mode');
    }
    try {
      const requestBody: any = {
        interface_type: interfaceType || "browser",
        interface_width: 1280,
        interface_height: 720,
        source: "SDK",
        open_page_on_start: openPageOnStart,
        env_id: envId,
        env_config: {},
        record_actions: recordActions,
        keepalive: keepalive,
        alias: alias,
        fast: fast,
      };

      // Only include artifact_id if it's provided for backward compatibility
      if (artifactId) {
        requestBody.artifact_id = artifactId;
      }

      const response = await this.http.post('/env/make2', requestBody);

      return new PlatoEnvironment(this, response.data.job_id, response.data.alias, fast);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  async getJobStatus(jobId: string) {
    try {
      const response = await this.http.get(`/env/${jobId}/status`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  async getCdpUrl(jobId: string): Promise<string> {
    try {
      const response = await this.http.get(`/env/${jobId}/cdp_url`);
      if (response.data.error) {
        throw new PlatoClientError(response.data.error);
      }
      return response.data.data.cdp_url;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  async closeEnvironment(jobId: string) {
    try {
      const response = await this.http.post(`/env/${jobId}/close`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  async evaluate(sessionId: string, value?: any) {
    try {
      let body = {};
      if (value) {
        body = {
          value: value,
        };
      }
      const response = await this.http.post(`/env/session/${sessionId}/evaluate`, body);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  /**
   * Resets an environment with a new task
   * @param jobId The ID of the job to reset
   * @param task The task to run in the environment, or a simplified object with just name, prompt, and start_url
   * @param testCasePublicId The public ID of the test case
   * @param loadAuthenticated Whether to load authenticated browser state
   * @param userId Optional user ID to associate with the reset
   * @returns The response from the server
   */
  async resetEnvironment(
    jobId: string,
    task?: PlatoTask | { name: string; prompt: string; start_url: string },
    testCasePublicId?: string,
    loadAuthenticated: boolean = false,
    userId?: number
  ) {
    try {
      const response = await this.http.post(`/env/${jobId}/reset`, {
        task: task || null,
        test_case_public_id: testCasePublicId || null,
        load_browser_state: loadAuthenticated,
        user_id: userId || null,
      });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  async getEnvironmentState(jobId: string) {
    try {
      const response = await this.http.get(`/env/${jobId}/state`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  async getWorkerReady(jobId: string): Promise<WorkerReadyResponse> {
    try {
      const response = await this.http.get(`/env/${jobId}/worker_ready`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }
  async getLiveViewUrl(jobId: string): Promise<string> {
    try {
        const workerStatus = await this.getWorkerReady(jobId);
        if (!workerStatus.ready) {
            throw new PlatoClientError('Worker is not ready yet');
        }
        return `${this.baseUrl}/live/${jobId}/`;
    }
    catch (error) {
        if (axios.isAxiosError(error)) {
            throw new PlatoClientError(error.message);
        }
        throw error;
    }
  }

  async sendHeartbeat(jobId: string) {
    try {
      const response = await this.http.post(`/env/${jobId}/heartbeat`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }

  async backupEnvironment(jobId: string) {
    try {
      const response = await this.http.post(`/env/${jobId}/backup`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new PlatoClientError(error.message);
      }
      throw error;
    }
  }
}
