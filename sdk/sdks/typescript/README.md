# Plato TypeScript SDK

TypeScript/JavaScript client library for the Plato platform - manage sandbox VMs, simulators, and environments programmatically.

## Installation

```bash
npm install plato-sdk
```

## Quick Start

```typescript
import { ApiClient } from 'plato-sdk';

// Initialize the client
const client = new ApiClient({
  baseUrl: 'https://api.plato.so',
  // Or use environment for predefined endpoints
  // environment: 'production'
});

// Create an environment
const response = await client.makeEnvironment({
  interface_type: 'desktop',
  env_id: 'my-env-001'
});

console.log('Environment created:', response);
```

## Features

- Full TypeScript support with generated types
- Promise-based API with async/await
- Built-in error handling and retries
- Request/response interceptors
- Timeout configuration
- Comprehensive API coverage for:
  - Environment management
  - Sandbox operations
  - Simulator control
  - Worker management
  - Snapshot creation
  - SSH and proxy access

## Usage

### Client Configuration

```typescript
import { ApiClient } from 'plato-sdk';

const client = new ApiClient({
  baseUrl: 'https://api.plato.so',
  headers: {
    'Authorization': 'Bearer your-api-token'
  },
  timeoutInSeconds: 60,
  maxRetries: 3
});
```

### Environment Operations

```typescript
// Create an environment
const env = await client.makeEnvironment({
  interface_type: 'desktop',
  env_id: 'my-environment',
  variables: [
    { key: 'DATABASE_URL', value: 'postgresql://...' }
  ]
});

// Check job status
const status = await client.getJobStatus('job-123');

// Get environment state
const state = await client.getEnvironmentState({
  env_id: 'my-environment'
});

// Close environment
await client.closeEnvironment('my-environment');
```

### Sandbox Management

```typescript
// Create a sandbox
const sandbox = await client.createSandbox({
  simulator_name: 'ubuntu-22.04',
  env_vars: {
    NODE_ENV: 'production'
  }
});

// Setup sandbox
await client.setupSandbox({
  sandbox_id: sandbox.sandbox_id,
  commands: ['npm install', 'npm run build']
});

// Delete sandbox
await client.deleteSandbox(sandbox.sandbox_id);
```

### Helper Functions

The SDK includes high-level helper functions that combine API calls with operation monitoring:

```typescript
import { ApiClient } from 'plato-sdk';
import { SandboxHelpers } from 'plato-sdk/helpers';

const client = new ApiClient({ baseUrl: 'https://api.plato.so' });
const helpers = new SandboxHelpers(client);

// Create and wait for sandbox to be ready
const sandbox = await helpers.createSandbox(
  {
    simulator_name: 'ubuntu-22.04',
    env_vars: { NODE_ENV: 'production' }
  },
  {
    wait: true,  // Wait for operation to complete
    pollInterval: 2000,  // Check every 2 seconds
    maxWaitTime: 300000  // Max 5 minutes
  }
);

// Setup sandbox with automatic monitoring
await helpers.setupSandbox(
  sandbox.sandbox_id,
  {
    commands: ['npm install'],
    files: { '/app/config.json': '{"env":"prod"}' }
  },
  { wait: true }
);
```

### Working with Simulators

```typescript
// List available simulators
const simulators = await client.listSimulators();

// Get simulator details
const simulator = await client.getSimulator('ubuntu-22.04');

// Start a worker
const worker = await client.startWorker({
  simulator_name: 'ubuntu-22.04',
  worker_id: 'worker-001'
});
```

### Snapshot Management

```typescript
// Create a snapshot
const snapshot = await client.createSnapshot({
  sandbox_id: 'sandbox-123',
  snapshot_name: 'backup-v1'
});

// Backup environment
await client.backupEnvironment('env-123');

// Reset environment
await client.resetEnvironment({
  env_id: 'env-123',
  snapshot_id: 'snapshot-456'
});
```

### Error Handling

```typescript
import { ApiError, ApiTimeoutError, BadRequestError } from 'plato-sdk';

try {
  await client.makeEnvironment({
    interface_type: 'desktop',
    env_id: 'my-env'
  });
} catch (error) {
  if (error instanceof BadRequestError) {
    console.error('Invalid request:', error.body);
  } else if (error instanceof ApiTimeoutError) {
    console.error('Request timed out');
  } else if (error instanceof ApiError) {
    console.error('API error:', error.statusCode, error.body);
  } else {
    throw error;
  }
}
```

### Request Options

Per-request configuration options:

```typescript
await client.makeEnvironment(
  { interface_type: 'desktop', env_id: 'my-env' },
  {
    timeoutInSeconds: 120,
    maxRetries: 5,
    headers: {
      'X-Custom-Header': 'value'
    },
    abortSignal: abortController.signal
  }
);
```

## API Reference

### Core Types

All API types are exported from `plato-sdk/api`:

```typescript
import type * as Api from 'plato-sdk/api';

const request: Api.MakeEnvironmentRequest = {
  interface_type: 'desktop',
  env_id: 'my-env'
};
```

### Main Classes

- `ApiClient` - Main API client
- `SandboxHelpers` - High-level sandbox operations
- `SandboxMonitor` - Operation monitoring utilities

### Error Types

- `ApiError` - Generic API error
- `ApiTimeoutError` - Request timeout
- `BadRequestError` - 400 Bad Request

## Advanced Usage

### Custom Base URL

```typescript
const client = new ApiClient({
  baseUrl: process.env.PLATO_API_URL || 'https://api.plato.so'
});
```

### Request Interceptors

```typescript
const client = new ApiClient({
  baseUrl: 'https://api.plato.so',
  headers: {
    'Authorization': `Bearer ${getToken()}`
  }
});
```

### Monitoring Operations

```typescript
import { SandboxMonitor } from 'plato-sdk/helpers';

const monitor = new SandboxMonitor(client);

const result = await monitor.waitForOperation(
  'operation-123',
  {
    pollInterval: 1000,
    maxWaitTime: 60000,
    onProgress: (event) => {
      console.log('Operation progress:', event.status);
    }
  }
);
```

## TypeScript Support

This SDK is written in TypeScript and includes full type definitions:

```typescript
import { ApiClient, type BaseClientOptions } from 'plato-sdk';
import type * as Api from 'plato-sdk/api';

const options: BaseClientOptions = {
  baseUrl: 'https://api.plato.so'
};

const client = new ApiClient(options);

// Full type inference
const response: Api.MakeEnvironmentResponse =
  await client.makeEnvironment({
    interface_type: 'desktop',
    env_id: 'my-env'
  });
```

## Requirements

- Node.js 18.0.0 or higher
- TypeScript 5.0+ (for TypeScript projects)

## Development

```bash
# Install dependencies
npm install

# Build the SDK
npm run build

# The compiled output will be in the current directory
```

## License

MIT

## Support

- GitHub Issues: https://github.com/plato-ai/plato-client/issues
- Documentation: https://github.com/plato-ai/plato-client#readme

## Related Projects

- [Plato Python SDK](../../python/) - Python client library
- [Plato CLI](../../cli/) - Command-line interface
- [Plato Go SDK](../../sdk/) - Core Go implementation
