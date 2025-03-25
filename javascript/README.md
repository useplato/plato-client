# Plato JavaScript/TypeScript Client

A JavaScript/TypeScript client library for interacting with the Plato API. This library provides a simple interface for creating and managing browser automation environments.

## Installation

```bash
npm install @plato-ai/client
```

## Configuration

The client can be configured using environment variables or by passing options directly to the client constructor:

```typescript
// Using environment variables (.env file)
PLATO_API_KEY=your_api_key
PLATO_BASE_URL=https://plato.so/api  # Optional, defaults to https://plato.so/api

// Or configure programmatically
const plato = new Plato('your_api_key', 'https://plato.so/api');
```

## Basic Usage

```typescript
import { Plato } from 'plato-sdk';

async function main() {
  // Create a client instance
  const plato = new Plato('your_api_key');

  // Create a new environment
  const env = await plato.makeEnvironment('test-env');

  // Get the CDP URL for browser automation
  const cdpUrl = await env.getCdpUrl();
  console.log('CDP URL:', cdpUrl);

  // Get the live view URL for visual monitoring
  const liveViewUrl = await env.getLiveViewUrl();
  console.log('Live View URL:', liveViewUrl);

  // Close the environment when done
  await env.close();
}

main().catch(console.error);
```

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

// Send heartbeat to keep worker alive
await plato.sendHeartbeat(env.id);
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

#### Methods

- `makeEnvironment(envId: string): Promise<PlatoEnvironment>`
- `getJobStatus(jobId: string): Promise<any>`
- `getCdpUrl(jobId: string): Promise<string>`
- `closeEnvironment(jobId: string): Promise<any>`
- `resetEnvironment(jobId: string, task?: PlatoTask): Promise<any>`
- `getEnvironmentState(jobId: string): Promise<any>`
- `getWorkerReady(jobId: string): Promise<any>`
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT

