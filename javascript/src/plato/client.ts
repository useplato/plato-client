import axios, { AxiosInstance } from 'axios';
import { getConfig } from './config';
import { PlatoClientError } from './exceptions';
import { z } from 'zod';

export const PlatoTaskSchema = z.object({
  // Add task schema fields as needed
});

export type PlatoTask = z.infer<typeof PlatoTaskSchema>;

export class PlatoEnvironment {
  private client: Plato;
  public id: string;

  constructor(client: Plato, id: string) {
    this.client = client;
    this.id = id;
  }

  async getStatus() {
    return this.client.getJobStatus(this.id);
  }

  async getCdpUrl() {
    return this.client.getCdpUrl(this.id);
  }

  async close() {
    return this.client.closeEnvironment(this.id);
  }

  async reset(task?: PlatoTask) {
    return this.client.resetEnvironment(this.id, task);
  }

  async getState() {
    return this.client.getEnvironmentState(this.id);
  }

  async getLiveViewUrl() {
    return this.client.getLiveViewUrl(this.id);
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
      const workerStatus = await this.client.getWorkerReady(this.id);
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

  constructor(apiKey?: string, baseUrl?: string) {
    const config = getConfig();
    this.apiKey = apiKey || config.apiKey;
    this.baseUrl = baseUrl || config.baseUrl;

    this.http = axios.create({
      baseURL: this.baseUrl,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
      },
    });
  }

  async makeEnvironment(envId: string): Promise<PlatoEnvironment> {
    try {
      const response = await this.http.post('/env/make', {
        config: {
          type: 'browser',
          browser_config: {
            type: 'playwright',
            cdp_port: 9222,
            headless: false,
            viewport_size: [1920, 1080],
          },
          simulator_config: {
            type: 'proxy',
            env_id: envId,
            num_workers: 4,
            proxy_config: {
              host: 'localhost',
              port: 8000,
            },
          },
          recording_config: {
            record_rrweb: true,
            record_network_requests: true,
          },
        },
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

  async resetEnvironment(jobId: string, task?: PlatoTask) {
    try {
      const response = await this.http.post(`/env/${jobId}/reset`, {
        task: task || null,
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

  async getWorkerReady(jobId: string) {
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
      
      const workerPublicIp = workerStatus.worker_public_ip;
      if (!workerPublicIp) {
        throw new PlatoClientError('Worker public IP not available');
      }
      
      return `http://${workerPublicIp}:6080`;
    } catch (error) {
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