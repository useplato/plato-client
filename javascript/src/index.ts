/** This module provides classes and methods for interacting with the Plato API. */
import { zodToJsonSchema } from 'zod-to-json-schema';
import { z } from 'zod';

const BASE_URL = "https://plato.so";

interface TestCase {
  name: string;
  prompt: string;
  startUrl?: string;
  outputSchema?: z.ZodSchema;
  [key: string]: any;
}
interface PlatoInitOptions {
  baseUrl?: string;
  apiKey?: string;
}

interface StartSimulationOptions {
  cdpUrl?: string;
}

interface Evaluator {
  data: TestCase[];
  task: (input: TestCase, startPlatoSimulation: (options: StartSimulationOptions) => Promise<PlatoSession>) => Promise<any>;
  customScores: ((args: {input: TestCase, output: any, expected: any}) => Promise<CustomScore>)[];
  name: string;
  trialCount?: number;
  timeout?: number;
  maxConcurrency?: number;
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

class PlatoEvaluator {
  plato: Plato;
  evaluator: Evaluator;
  maxConcurrency: number;
  trialCount: number;
  timeout: number;
  customScores: ((args: {input: TestCase, output: any, expected: any}) => Promise<CustomScore>)[];

  constructor(plato: Plato, evaluator: Evaluator) {
    this.plato = plato;
    this.evaluator = evaluator;

    this.maxConcurrency = evaluator.maxConcurrency || 15;
    this.trialCount = evaluator.trialCount || 1;
    this.timeout = evaluator.timeout || 1800000;
    this.customScores = evaluator.customScores || [];
  }

  async _runTask(input: TestCase): Promise<any> {
    let simulatorSession: PlatoSession;
    try {
      const output = await this.evaluator.task(input, async (options) => {
        simulatorSession = await this.plato.startSimulation(input, options);
        return simulatorSession;
      });
      const customScores = await Promise.all((this.evaluator.customScores ||[]).map(async score => {
        const scoreResult = await score({input, output, expected: input.expected});
        await simulatorSession.score(scoreResult);
        return scoreResult;
      }));
      return { input, output, customScores };
    } catch (err) {
      console.error('Error running task', err);
    }
  }

  async run(): Promise<EvalResult> {
    const results: any[] = [];
    const tasks = this.evaluator.data.flatMap(input =>
      Array(this.trialCount).fill(input)
    );

    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Evaluation timeout')), this.timeout);
    });

    try {
      const queue = [...tasks];

      const processTask = async () => {
        while (queue.length > 0) {
          const input = queue.shift()!;
          try {
            const result = await this._runTask(input);
            results.push(result);
          } catch (error) {
            console.error(error);
          }
        }
      };

      await Promise.race([
        Promise.all([
          ...Array(Math.min(this.maxConcurrency, tasks.length))
            .fill(null)
            .map(() => processTask())
        ]),
        timeoutPromise
      ]);

      const summary: EvalSummary = {
        total: results.length,
        success: results.filter(r => r.score > 0).length,
        failure: results.filter(r => r.score <= 0).length,
        score: results.reduce((acc, r) => acc + r.score, 0) / results.length
      };

      return {
        summary,
        results
      };
    } catch (error) {
      if (error instanceof Error && error.message === 'Evaluation timeout') {
        throw new Error(`Evaluation timed out after ${this.timeout}ms`);
      }
      throw error;
    }
  }

}


export default class Plato {
  apiKey: string;
  baseUrl: string;
  name: string;
  runBatchId: string;

  constructor(apiKey: string, baseUrl = BASE_URL, name: string, runBatchId: string) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.name = name;
    this.runBatchId = runBatchId;
  }

  /**
   * Creates a PlatoEvaluator
   * @param name
   * @param evaluator
   * @param options
   * @returns
   */
  static async Eval(name: string, evaluator: Evaluator, options: PlatoInitOptions = {}) {
    const baseUrl = options.baseUrl || BASE_URL;
    const apiKey = options.apiKey || process.env.PLATO_API_KEY;

    if (!apiKey) {
      throw new Error('PLATO_API_KEY is not set');
    }

    const response = await fetch(`${baseUrl}/api/runs/group`, {
      method: 'POST',
      body: JSON.stringify({
        name: evaluator.name,
      }),
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to initialize Plato: ${response.statusText}`);
    }

    const data = await response.json();

    const plato = new Plato(apiKey, baseUrl, name, data.publicId);
    const platoEvaluator = new PlatoEvaluator(plato, evaluator);
    return platoEvaluator.run();
  }


  /**
   * Initializes a new Plato instance
   * @param name
   * @param options
   * @returns
   */
  static async init(name: string, options: PlatoInitOptions = {}) {
    const baseUrl = options.baseUrl || BASE_URL;
    const apiKey = options.apiKey || process.env.PLATO_API_KEY;

    if (!apiKey) {
      throw new Error('PLATO_API_KEY is not set');
    }

    const response = await fetch(`${baseUrl}/api/runs/group`, {
      method: 'POST',
      body: JSON.stringify({
        name,
      }),
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to initialize Plato: ${response.statusText}`);
    }

    const data = await response.json();
    return new Plato(apiKey, baseUrl, name, data.publicId);
  }


  async startSimulation(testCase: TestCase, options: StartSimulationOptions = {}): Promise<PlatoSession> {
    return PlatoSession.start(this, testCase, options);
  }

}


export class PlatoSession {
  private plato: Plato;
  private testCase: TestCase;
  public cdpUrl: string;
  private sessionId: string;

  constructor(plato: Plato, testCase: TestCase, cdpUrl: string, sessionId: string) {
    this.plato = plato;
    this.testCase = testCase;
    this.cdpUrl = cdpUrl;
    this.sessionId = sessionId;
  }

  static async start(plato: Plato, testCase: TestCase, options: StartSimulationOptions = {}): Promise<PlatoSession> {
    const response = await fetch(`${plato.baseUrl}/api/runs/group/${plato.runBatchId}/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': plato.apiKey
      },
      body: JSON.stringify({
        version: plato.name,
        testCase: {
          ...testCase,
          outputSchema: testCase.outputSchema ? zodToJsonSchema(testCase.outputSchema) : undefined
        },
        ...options,
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`);
    }

    const data = await response.json();

    const sessionId = data.session_id;
    let cdpUrl;

    // poll /api/runs/{session_id} until it has a cdp url. max timeout of 10m
    const timeoutAt = Date.now() + 600000;
    while (Date.now() < timeoutAt) {
      const response = await fetch(`${plato.baseUrl}/api/runs/${sessionId}`);
      const data = await response.json();
      if (data.cdpUrl || !['run_queued', 'run_started'].includes(data.status)) {
        cdpUrl = data.cdpUrl;
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 3000));
    }

    if (!cdpUrl) {
      await PlatoSession.terminate(plato, sessionId);
      throw new Error('Failed to start browser session');
    }

    const session = new PlatoSession(plato, testCase, cdpUrl, sessionId);
    return session;
  }

  static async terminate(plato: Plato, sessionId: string): Promise<void> {
    try {
      await fetch(`${plato.baseUrl}/api/runs/${sessionId}/terminate`, {
        method: 'POST',
        headers: {
            'x-api-key': plato.apiKey
          }
        });
    } catch (error) {
      console.warn('Error terminating session', error);
    }
  }

  async end(): Promise<void> {

  }

  async log(message: string): Promise<void> {
    try {
      await fetch(`${this.plato.baseUrl}/api/runs/${this.sessionId}/log`, {
        method: 'POST',
        headers: {
          'x-api-key': this.plato.apiKey
        },
        body: JSON.stringify({ message, timestamp: new Date().toISOString() })
      });
    } catch (error) {
      console.log('Error logging', error);
    }
  }

  async score(score: CustomScore): Promise<void> {
    try {
      const response = await fetch(`${this.plato.baseUrl}/api/runs/${this.sessionId}/score`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.plato.apiKey
        },
        body: JSON.stringify({ score: score.score, name: score.name })
      });

      if (!response.ok) {
        throw new Error(`Failed to score: ${response.statusText}`);
      }
    } catch (error) {
      console.log('Error scoring', error);
    }
  }
}
