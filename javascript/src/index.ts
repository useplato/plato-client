/** This module provides classes and methods for interacting with the Plato API. */

import axios, { type AxiosResponse } from 'axios';
import { URL } from 'url';
import { ZodSchema } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

const BASE_URL = "https://plato.so";

export default class Plato {
  apiKey: string;
  baseUrl: string;
  cookies?: Record<string, any>;

  constructor(apiKey: string, baseUrl: string = BASE_URL, cookies?: Record<string, any>) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.cookies = cookies;
  }

  async startSession(): Promise<PlatoSession> {
    const session = new PlatoSession(this);
    await session.start();
    return session;
  }
}

export class PlatoSession {
  private plato: Plato;
  private sessionId: string | null = null;

  constructor(plato: Plato) {
    this.plato = plato;
  }

  private get apiUrl(): string {
    const url = new URL(this.plato.baseUrl);
    const port = url.port ? `:${url.port}` : '';
    return `${url.protocol}//api.${url.hostname}${port}`;
  }

  private get chromeWsUrl(): string {
    const url = new URL(this.plato.baseUrl);
    const port = url.port ? `:${url.port}` : '';
    return `${url.protocol === 'https:' ? 'wss' : 'ws'}://${url.hostname}${port}/ws?session_id=${this.sessionId}`;
  }

  private get browserUrl(): string {
    const url = new URL(this.plato.baseUrl);
    const port = url.port ? `:${url.port}` : '';
    return `${url.protocol}//browser.${url.hostname}${port}/plato?session_id=${this.sessionId}`;
  }

  async start(): Promise<void> {
    const response: AxiosResponse = await axios.post(`${this.apiUrl}/start-session`, {
      cookies: this.plato.cookies
    }, {
      headers: { Authorization: `Bearer ${this.plato.apiKey}` }
    });
    this.sessionId = response.data.session_id;
    console.log("Started Plato browser session", this.browserUrl);
  }

  async end(): Promise<any> {
    const response: AxiosResponse = await axios.post(`${this.apiUrl}/end-session`, {
      session_id: this.sessionId
    }, {
      headers: { Authorization: `Bearer ${this.plato.apiKey}` }
    });
    return response.data;
  }

  async navigate(url: string): Promise<any> {
    const response: AxiosResponse = await axios.post(`${this.apiUrl}/navigate`, {
      session_id: this.sessionId,
      url: url
    }, {
      headers: { Authorization: `Bearer ${this.plato.apiKey}` }
    });
    return response.data;
  }

  async click(description: string): Promise<any> {
    const response: AxiosResponse = await axios.post(`${this.apiUrl}/click`, {
      session_id: this.sessionId,
      description: description
    }, {
      headers: { Authorization: `Bearer ${this.plato.apiKey}` }
    });
    return response.data;
  }

  async type(text: string): Promise<any> {
    const response: AxiosResponse = await axios.post(`${this.apiUrl}/type`, {
      session_id: this.sessionId,
      text: text
    }, {
      headers: { Authorization: `Bearer ${this.plato.apiKey}` }
    });
    return response.data;
  }

  async extract<T>(description: string, { responseFormat }: { responseFormat: ZodSchema<T> }): Promise<T> {
    const jsonSchema = zodToJsonSchema(responseFormat);
    const response: AxiosResponse = await axios.post(`${this.apiUrl}/extract`, {
      session_id: this.sessionId,
      description: description,
      response_format: jsonSchema
    }, {
      headers: { Authorization: `Bearer ${this.plato.apiKey}` }
    });
    return responseFormat.parse(response.data);
  }

  async task<T>(task: string, { startUrl, responseFormat }: { startUrl?: string, responseFormat?: ZodSchema<T> }): Promise<T | any> {
    const jsonSchema = responseFormat ? zodToJsonSchema(responseFormat) : undefined;
    const response: AxiosResponse = await axios.post(`${this.apiUrl}/task`, {
      session_id: this.sessionId,
      task: task,
      start_url: startUrl,
      response_format: jsonSchema
    }, {
      headers: { Authorization: `Bearer ${this.plato.apiKey}` }
    });
    return responseFormat ? responseFormat.parse(response.data) : response.data;
  }

  monitor(url: string, ...args: any[]): void {
    // Implement monitoring logic here
  }

  job(jobId: string, ...args: any[]): void {
    // Implement job retrieval logic here
  }

  async dispose(): Promise<void> {
    await this.end();
  }
}
