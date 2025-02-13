/** This module provides classes and methods for interacting with the Plato API. */
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

const DEFAULT_BASE_URL = "https://plato.so";

interface Task {
  name: string;
  prompt: string;
  startUrl?: string;
  outputSchema?: z.ZodSchema;
  expected?: any;
  [key: string]: any;
}

interface PlatoRunnerConfig {
  name: string;
  data: Task[];
  task: (input: Task, cdpUrl: string) => Promise<any>;
  trialCount?: number;
  timeout?: number;
  maxConcurrency?: number;
  customBrowser?: (task: Task) => Promise<string>;
  customScores?: ((args: {input: Task, output: any, expected: any}) => Promise<CustomScore>)[];
}

interface EvalSummary {
  total: number;
  success: number;
  failure: number;
  score: number;
}

interface EvalResult {
  summary: EvalSummary;
  results: any[];
}

interface CustomScore {
  name: string;
  score: number;
}

export default class Plato {
  private apiKey: string;
  private baseUrl: string;
  private name: string;
  private runBatchId: string;
  private config: PlatoRunnerConfig;

  constructor(apiKey: string, baseUrl: string, name: string, runBatchId: string, config: PlatoRunnerConfig) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.name = name;
    this.runBatchId = runBatchId;
    this.config = config;
  }

  // Getters for PlatoSession to access private properties
  getApiKey(): string {
    return this.apiKey;
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  getName(): string {
    return this.name;
  }

  getRunBatchId(): string {
    return this.runBatchId;
  }

  getConfig(): PlatoRunnerConfig {
    return this.config;
  }

  private async _runTask(task: Task): Promise<any> {
    let session: PlatoSession | undefined;
    try {
      session = await PlatoSession.start(this, task);
      const output = await this.config.task(task, session.cdpUrl);
      const customScores = await Promise.all((this.config.customScores || []).map(async score => {
        return await score({
          input: task,
          output,
          expected: task.expected
        });
      }));
      return {
        input: task,
        output,
        customScores
      };
    } finally {
      if (session) {
        await session.close();
      }
    }
  }

  async run(): Promise<EvalResult> {
    const results: any[] = [];
    const tasks = this.config.data.flatMap(task =>
      Array(this.config.trialCount || 1).fill(task)
    );

    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Evaluation timeout')), this.config.timeout || 1800000);
    });

    try {
      const queue = [...tasks];
      const maxConcurrency = this.config.maxConcurrency || 15;
      const semaphore = new Array(Math.min(maxConcurrency, tasks.length))
        .fill(null)
        .map(() => {
          return (async () => {
            while (queue.length > 0) {
              const task = queue.shift()!;
              try {
                const result = await this._runTask(task);
                results.push(result);
              } catch (error) {
                console.error('Error processing task:', error);
              }
            }
          })();
        });

      await Promise.race([Promise.all(semaphore), timeoutPromise]);

      const total = results.length;
      const success = results.filter(r => r.score > 0).length;
      const failure = total - success;
      const averageScore = results.reduce((acc, r) => acc + (r.score || 0), 0) / total;

      const summary: EvalSummary = {
        total,
        success,
        failure,
        score: averageScore
      };

      return {
        summary,
        results
      };
    } catch (error) {
      if (error instanceof Error && error.message === 'Evaluation timeout') {
        throw new Error(`Evaluation timed out after ${this.config.timeout || 1800000}ms`);
      }
      throw error;
    }
  }

  static async start(
    name: string,
    config: PlatoRunnerConfig,
    options: { apiKey?: string; baseUrl?: string; } = {}
  ): Promise<EvalResult> {
    const baseUrl = options.baseUrl || DEFAULT_BASE_URL;
    const apiKey = options.apiKey || process.env.PLATO_API_KEY;

    if (!apiKey) {
      throw new Error('PLATO_API_KEY is not set');
    }

    const response = await fetch(`${baseUrl}/api/runs/group`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey
      },
      body: JSON.stringify({ name: config.name })
    });

    if (!response.ok) {
      throw new Error(`Failed to initialize Plato: ${response.statusText}`);
    }

    const data = await response.json();
    const runBatchId = data.publicId;

    if (!runBatchId) {
      throw new Error('No run batch ID returned from Plato API');
    }

    const plato = new Plato(apiKey, baseUrl, name, runBatchId, config);
    return plato.run();
  }

  static async getDataset(
    datasetId: string,
    options: { apiKey?: string; baseUrl?: string; } = {}
  ): Promise<Task[]> {
    const baseUrl = options.baseUrl || DEFAULT_BASE_URL;
    const apiKey = options.apiKey || process.env.PLATO_API_KEY;

    if (!apiKey) {
      throw new Error('PLATO_API_KEY is not set');
    }

    const response = await fetch(`${baseUrl}/api/testcases/sets/${datasetId}/testcases`, {
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get dataset: ${response.statusText}`);
    }

    const data = await response.json();
    if (!data.success) {
      throw new Error(`Failed to get dataset: ${data.message}`);
    }

    return data.testcases;
  }
}

export class PlatoSession {
  private plato: Plato;
  private task: Task;
  public cdpUrl: string;
  private sessionId: string;

  constructor(plato: Plato, task: Task, cdpUrl: string, sessionId: string) {
    this.plato = plato;
    this.task = task;
    this.cdpUrl = cdpUrl;
    this.sessionId = sessionId;
  }

  static async start(plato: Plato, task: Task): Promise<PlatoSession> {
    const headers = {
      'Content-Type': 'application/json',
      'x-api-key': plato.getApiKey()
    };

    const response = await fetch(`${plato.getBaseUrl()}/api/runs/group/${plato.getRunBatchId()}/run`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        version: plato.getName(),
        testCase: {
          ...task,
          outputSchema: task.outputSchema ? zodToJsonSchema(task.outputSchema) : undefined
        }
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`);
    }

    const data = await response.json();
    const sessionId = data.session_id;

    if (!sessionId) {
      throw new Error('No session_id returned from Plato API');
    }

    let cdpUrl: string | undefined;

    // If custom browser is provided, use it
    const customBrowser = plato.getConfig().customBrowser;
    if (customBrowser) {
      cdpUrl = await customBrowser(task);
    } else {
      // Poll for CDP URL
      const timeoutMs = 60000; // 1 minute
      const startTime = Date.now();

      while (Date.now() - startTime < timeoutMs) {
        const resp = await fetch(`${plato.getBaseUrl()}/api/runs/${sessionId}`);
        const runData = await resp.json();
        if (runData.cdpUrl) {
          cdpUrl = runData.cdpUrl;
          break;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    if (!cdpUrl) {
      throw new Error('Failed to start browser session');
    }

    return new PlatoSession(plato, task, cdpUrl, sessionId);
  }

  static async terminate(plato: Plato, sessionId: string): Promise<void> {
    try {
      await fetch(`${plato.getBaseUrl()}/api/runs/${sessionId}/terminate`, {
        method: 'POST',
        headers: {
          'x-api-key': plato.getApiKey()
        }
      });
    } catch (error) {
      console.warn('Error terminating session:', error);
    }
  }

  async close(): Promise<void> {
    return PlatoSession.terminate(this.plato, this.sessionId);
  }

  async log(message: string): Promise<void> {
    try {
      await fetch(`${this.plato.getBaseUrl()}/api/runs/${this.sessionId}/log`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.plato.getApiKey()
        },
        body: JSON.stringify({ message })
      });
    } catch (error) {
      console.warn('Error logging:', error);
    }
  }

  async score(score: CustomScore): Promise<void> {
    try {
      const response = await fetch(`${this.plato.getBaseUrl()}/api/runs/${this.sessionId}/score`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.plato.getApiKey()
        },
        body: JSON.stringify(score)
      });

      if (!response.ok) {
        throw new Error(`Failed to score: ${response.statusText}`);
      }
    } catch (error) {
      console.warn('Error scoring:', error);
    }
  }
}
