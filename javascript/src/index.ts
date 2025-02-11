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

interface Evaluator {
  data: TestCase[];
  task: (input: TestCase, simulatorSession: PlatoSession) => Promise<any>;
  customScores: ((args: {input: TestCase, output: any, expected: any}) => Promise<number>)[];
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

export default class Plato {
  apiKey: string;
  baseUrl: string;
  name: string;
  runBatchId: string;
  evaluator: Evaluator;
  maxConcurrency: number;
  trialCount: number;
  timeout: number;

  constructor(apiKey: string, baseUrl = BASE_URL, name: string, runBatchId: string, evaluator: Evaluator) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.name = name;
    this.runBatchId = runBatchId;
    this.evaluator = evaluator;

    this.maxConcurrency = evaluator.maxConcurrency || 15;
    this.trialCount = evaluator.trialCount || 1;
    this.timeout = evaluator.timeout || 1800000;
  }

  async _runTask(input: TestCase): Promise<any> {
    const simulatorSession = await PlatoSession.start(this, input);
    try {
      const output = await this.evaluator.task(input, simulatorSession);
      const customScores = await Promise.all((this.evaluator.customScores ||[]).map(score => score({input, output, expected: input.expected})));
      return { input, output, customScores };
    } finally {
      await simulatorSession.end();
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

    const plato = new Plato(apiKey, baseUrl, name, data.publicId, evaluator);

    return plato.run();
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

  static async start(plato: Plato, testCase: TestCase): Promise<PlatoSession> {
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
        }
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
    return;
  }

  async score(): Promise<void> {
    return;
  }
}
