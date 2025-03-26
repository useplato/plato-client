# Plato JavaScript/TypeScript Client

A JavaScript/TypeScript client library for interacting with the Plato API. This library provides a simple interface for creating and managing browser automation environments.

## Installation

```bash
npm install @plato-ai/client
```

## Configuration

The client must be configured by passing options directly to the client constructor:

```typescript
// Configure programmatically
const plato = new Plato('your_api_key', 'https://plato.so/api'); // API key is required, base URL is optional
```

## Basic Usage

```typescript
import { Plato } from 'plato-sdk';

async function main() {
  // Create a client instance with your API key
  const plato = new Plato('your_api_key');

  // Create a new environment
  const env = await plato.makeEnvironment('test-env');

  // Wait for the environment to be ready
  await env.waitForReady(60000); // timeout in ms (optional)

  // Get the CDP URL for browser automation
  const cdpUrl = await env.getCdpUrl();
  console.log('CDP URL:', cdpUrl);

  // Get the live view URL for visual monitoring
  const liveViewUrl = await env.getLiveViewUrl();
  console.log('Live View URL:', liveViewUrl);

  // Environment automatically sends heartbeats to keep it alive
  
  // When finished, close the environment - this also stops the heartbeats
  await env.close();
}

main().catch(console.error);
```

## Playwright Integration

The library includes built-in support for Playwright browser automation:

```typescript
import { Plato } from 'plato-sdk';
import { chromium } from 'playwright';

async function main() {
  // Create a client and environment
  const plato = new Plato('your_api_key');
  const env = await plato.makeEnvironment('playwright-test');
  
  // Wait for the environment to be ready
  await env.waitForReady();
  
  // Connect with Playwright using the built-in helper
  const { browser, context, page } = await env.connectWithPlaywright(chromium);
  
  // Use Playwright as normal
  await page.goto('https://example.com');
  await page.screenshot({ path: 'screenshot.png' });
  
  // Clean up
  await browser.close();
  await env.close();
}

main().catch(console.error);
```

## Browser Usage

This library is compatible with browser environments. When using in a browser, simply import the package and provide your API key:

```javascript
// In a browser environment
import { Plato } from 'plato-sdk';

// Create a client with your API key
const plato = new Plato('your_api_key');

// Use the client as normal
document.getElementById('createEnv').addEventListener('click', async () => {
  try {
    const env = await plato.makeEnvironment('browser-test');
    await env.waitForReady();
    const cdpUrl = await env.getCdpUrl();
    console.log('Environment ready with CDP URL:', cdpUrl);
  } catch (error) {
    console.error('Error:', error);
  }
});
```

## Automatic Heartbeats

The environment automatically sends heartbeats to keep the environment alive, so you don't need to manually implement a heartbeat mechanism. When you call `env.close()`, the heartbeats are automatically stopped.

## Advanced Usage

### Environment Management

```typescript
// Create an environment with custom configuration
const env = await plato.makeEnvironment('test-env');

// Check environment status
const status = await env.getStatus();
console.log('Environment Status:', status);

// Reset environment
await env.reset();

// Get environment state
const state = await env.getState();
console.log('Environment State:', state);
```

### Worker Management

```typescript
// Check if worker is ready
const workerStatus = await plato.getWorkerReady(env.id);
if (workerStatus.ready) {
  console.log('Worker is ready');
  console.log('Worker Public IP:', workerStatus.worker_public_ip);
}

// Heartbeats are sent automatically, you don't need to do this manually
```

### Error Handling

The library includes built-in error handling with custom error types:

```typescript
import { Plato, PlatoClientError } from '@plato-ai/client';

async function main() {
  try {
    const plato = new Plato('invalid_api_key');
    await plato.makeEnvironment('test-env');
  } catch (error) {
    if (error instanceof PlatoClientError) {
      console.error('Plato API Error:', error.message);
    } else {
      console.error('Unexpected error:', error);
    }
  }
}
```

## Examples

Check out the [examples](./examples) directory for more detailed usage examples:
- Basic environment creation and management
- Browser automation with CDP
- Worker management and monitoring
- Error handling and recovery

## API Reference

### `Plato`

Main client class for interacting with the Plato API.

#### Constructor

- `constructor(apiKey: string, baseUrl?: string)`

#### Methods

- `makeEnvironment(envId: string): Promise<PlatoEnvironment>`
- `getJobStatus(jobId: string): Promise<any>`
- `getCdpUrl(jobId: string): Promise<string>`
- `closeEnvironment(jobId: string): Promise<any>`
- `resetEnvironment(jobId: string, task?: PlatoTask): Promise<any>`
- `getEnvironmentState(jobId: string): Promise<any>`
- `getWorkerReady(jobId: string): Promise<WorkerReadyResponse>`
- `getLiveViewUrl(jobId: string): Promise<string>`
- `sendHeartbeat(jobId: string): Promise<any>`

### `PlatoEnvironment`

Class representing a Plato environment instance.

#### Methods

- `getStatus(): Promise<any>`
- `getCdpUrl(): Promise<string>`
- `close(): Promise<any>`
- `reset(task?: PlatoTask): Promise<any>`
- `getState(): Promise<any>`
- `getLiveViewUrl(): Promise<string>`
- `waitForReady(timeout?: number): Promise<void>`
- `connectWithPlaywright(playwrightLib: any): Promise<{ browser, context, page }>`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT

