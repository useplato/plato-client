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
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private heartbeatIntervalMs: number = 30000; // 30 seconds

  constructor(client: Plato, id: string) {
    this.client = client;
    this.id = id;
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
    return this.client.closeEnvironment(this.id);
  }

  /**
   * Resets the environment with a new task
   * @param task The task to run in the environment, or a simplified object with just name, prompt, and start_url
   * @returns The response from the server
   */
  async reset(task?: PlatoTask | { name: string; prompt: string; start_url: string }, test_case_public_id?: string) {
    const result = await this.client.resetEnvironment(this.id, task, test_case_public_id);
    // Ensure heartbeat is running after reset
    this.startHeartbeat();
    return result;
  }

  async getState() {
    return this.client.getEnvironmentState(this.id);
  }

  async getLiveViewUrl() {
    return this.client.getLiveViewUrl(this.id);
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
}

export class Plato {
  private apiKey: string;
  private baseUrl: string;
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
   * @returns The created environment instance
   * @throws PlatoClientError If the API request fails
   */
  async makeEnvironment(envId: string, openPageOnStart: boolean = false): Promise<PlatoEnvironment> {
    try {
      const response = await this.http.post('/env/make2', {
        interface_type: "browser",
        interface_width: 1280,
        interface_height: 720,
        source: "SDK",
        open_page_on_start: openPageOnStart,
        env_id: envId,
        env_config: {},
      });

      return new PlatoEnvironment(this, response.data.job_id);
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

  /**
   * Resets an environment with a new task
   * @param jobId The ID of the job to reset
   * @param task The task to run in the environment, or a simplified object with just name, prompt, and start_url
   * @returns The response from the server
   */
  async resetEnvironment(jobId: string, task?: PlatoTask | { name: string; prompt: string; start_url: string }, test_case_public_id?: string) {
    try {
      const response = await this.http.post(`/env/${jobId}/reset`, {
        task: task || null,
        test_case_public_id: test_case_public_id || null,
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
}
