/** This module provides classes and methods for interacting with the Plato API. */

import { URL } from 'url';
import { ZodSchema } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { z } from 'zod';

const BASE_URL = "https://plato.so";

interface TestCase {
  name: string;
  prompt: string;
  startUrl: string;
  outputSchema: z.ZodSchema;
}

interface PlatoInitOptions {
  baseUrl?: string;
}

export default class Plato {
  apiKey: string;
  baseUrl: string;
  version: string;

  runBatchId: string;

  constructor(apiKey: string, baseUrl = BASE_URL, version: string, runBatchId: string) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.version = version;
    this.runBatchId = runBatchId;
  }

  static async init(apiKey: string, version: string, options: PlatoInitOptions = {}): Promise<Plato> {
    const baseUrl = options.baseUrl || BASE_URL;
    const response = await fetch(`${baseUrl}/api/runs/group`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to initialize Plato: ${response.statusText}`);
    }

    const data = await response.json();
    const plato = new Plato(apiKey, baseUrl, version, data.publicId);
    plato.runBatchId = data.publicId;
    return plato;
  }

  async startSimulationSession(testCase: TestCase, options = {}): Promise<PlatoSession> {
    const session = await PlatoSession.start(this, testCase);
    return session;
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
        version: plato.version,
        testCase: {
          ...testCase,
          outputSchema: zodToJsonSchema(testCase.outputSchema)
        }
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`);
    }

    const data = await response.json();
    const session = new PlatoSession(plato, testCase, data.cdp_url, data.session_id);
    return session;
  }

  async log(message: string): Promise<void> {
    return;
  }

  async score(): Promise<void> {
    return;
  }
}
