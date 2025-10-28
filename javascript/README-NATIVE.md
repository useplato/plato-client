# Plato TypeScript SDK - Native Bindings

TypeScript client for the Plato Sandbox SDK using native bindings via FFI. This provides **100% feature parity** with the Python SDK by using the same underlying Go shared library.

## Features

✅ **Complete Feature Parity with Python SDK:**
- VM Sandbox management (create, delete, snapshot)
- SSE event monitoring with real-time progress
- Automatic background heartbeats
- Proxy tunnel management
- SSH setup and configuration
- Gitea integration
- Simulator management

✅ **Native Performance:** Direct FFI bindings to Go SDK
✅ **Minimal Code:** Reuses existing C bindings (same as Python)
✅ **Type Safety:** Full TypeScript type definitions

## Installation

### Prerequisites

1. **Node.js 16+** with npm
2. **Python build tools** (for node-gyp):
   - **macOS**: Xcode Command Line Tools (`xcode-select --install`)
   - **Linux**: `build-essential` (`apt-get install build-essential`)
   - **Windows**: Visual Studio Build Tools

### Install

```bash
npm install plato-sdk
```

Or from source:

```bash
# Clone repo
git clone https://github.com/plato-ai/plato-client.git
cd plato-client

# Build TypeScript SDK with native bindings
./scripts/build-typescript-bindings.sh

# Link for local development
cd javascript
npm link
```

## Quick Start

```typescript
import { PlatoSandboxClient } from 'plato-sdk/native';

const client = new PlatoSandboxClient('your-api-key');

// Create sandbox from artifact (waits until ready by default)
const sandbox = await client.createSandbox({
  artifactId: 'art_123456',
  wait: true,
});

console.log(`Sandbox ready at ${sandbox.url}`);

// Setup SSH access
const ssh = await client.setupSSH(sandbox);
console.log(`SSH command: ${ssh.ssh_command}`);

// Start proxy tunnel
const tunnel = await client.startProxyTunnel(sandbox.public_id, 8080);
console.log(`Access at http://localhost:${tunnel.local_port}`);

// Create snapshot
const snapshot = await client.createSnapshot(sandbox.public_id, {
  service: 'web',
  dataset: 'base',
});
console.log(`Snapshot: ${snapshot.artifact_id}`);

// Close sandbox (automatically stops heartbeat)
await client.closeSandbox(sandbox.public_id);
```

## API Reference

### `PlatoSandboxClient`

Main client class for managing sandboxes.

#### Constructor

```typescript
new PlatoSandboxClient(apiKey: string, baseUrl?: string)
```

- `apiKey` - Your Plato API key
- `baseUrl` - API base URL (default: 'https://plato.so/api')

#### Methods

##### `createSandbox(options)`

Create a new VM sandbox.

```typescript
await client.createSandbox({
  config?: SimConfigDataset,      // VM configuration
  artifactId?: string,             // Or create from artifact
  dataset?: string,                // Dataset name (default: 'base')
  alias?: string,                  // Human-readable alias
  service?: string,                // Service name
  wait?: boolean,                  // Wait until ready (default: true)
  timeout?: number,                // Timeout in seconds (default: 600)
});
```

**Returns:** `Promise<Sandbox>`

##### `closeSandbox(publicId)`

Close a sandbox and stop its heartbeat.

```typescript
await client.closeSandbox('sandbox-id');
```

##### `createSnapshot(publicId, request)`

Create a snapshot of a running sandbox.

```typescript
const snapshot = await client.createSnapshot('sandbox-id', {
  service: 'web',
  dataset: 'base',
  git_hash?: 'abc123',
});
```

**Returns:** `Promise<CreateSnapshotResponse>`

##### `startWorker(publicId, request)`

Start a Plato worker in a sandbox.

```typescript
await client.startWorker('sandbox-id', {
  dataset: 'base',
  plato_dataset_config: config,
});
```

##### `listSimulators()`

List all available simulators.

```typescript
const simulators = await client.listSimulators();
```

**Returns:** `Promise<SimulatorListItem[]>`

##### `getSimulatorVersions(simulatorName)`

Get all versions for a specific simulator.

```typescript
const versions = await client.getSimulatorVersions('espocrm');
```

##### `waitUntilReady(correlationId, timeout?)`

Wait for an operation to complete via SSE monitoring.

```typescript
await client.waitUntilReady('corr-123', 600);
```

##### `setupSSH(sandbox, options?)`

Setup SSH configuration for a sandbox.

```typescript
const sshInfo = await client.setupSSH(sandbox, {
  localPort: 2200,
  username: 'plato',
});

console.log(sshInfo.ssh_command);  // ssh sandbox-1
```

##### `startProxyTunnel(publicId, remotePort, localPort?)`

Start a proxy tunnel to the sandbox.

```typescript
const tunnel = await client.startProxyTunnel('sandbox-id', 8080, 0);
console.log(`http://localhost:${tunnel.local_port}`);
```

##### `stopProxyTunnel(tunnelId)`

Stop a running proxy tunnel.

```typescript
await client.stopProxyTunnel('tunnel_1');
```

##### `listProxyTunnels()`

List all active proxy tunnels.

```typescript
const tunnels = await client.listProxyTunnels();
```

### Gitea Methods

##### `getGiteaCredentials()`

Get Gitea admin credentials.

```typescript
const creds = await client.getGiteaCredentials();
```

##### `listGiteaSimulators()`

List simulators with Gitea repository info.

```typescript
const sims = await client.listGiteaSimulators();
```

##### `getGiteaRepository(simulatorId)`

Get repository details for a simulator.

```typescript
const repo = await client.getGiteaRepository(123);
```

##### `createGiteaRepository(simulatorId)`

Create a repository for a simulator.

```typescript
const repo = await client.createGiteaRepository(123);
```

##### `pushToGitea(serviceName, sourceDir?)`

Push code to Gitea on a timestamped branch.

```typescript
const result = await client.pushToGitea('my-service', './src');
console.log(`Branch: ${result.BranchName}`);
```

##### `mergeToMain(serviceName, branchName)`

Merge a branch to main.

```typescript
const gitHash = await client.mergeToMain('my-service', 'feature-branch');
```

## Type Definitions

All types are exported from the module:

```typescript
import {
  PlatoSandboxClient,
  SimConfigDataset,
  SimConfigCompute,
  SimConfigMetadata,
  Sandbox,
  CreateSnapshotRequest,
  CreateSnapshotResponse,
  StartWorkerRequest,
  StartWorkerResponse,
  SimulatorListItem,
  GiteaCredentials,
  GiteaRepository,
  ProxyTunnelInfo,
  SSHInfo,
} from 'plato-sdk/native';
```

## Comparison: Native vs HTTP Client

| Feature | Native Bindings | HTTP Client |
|---------|----------------|-------------|
| **Environment** | Node.js only | Node.js + Browser |
| **Dependencies** | Native (FFI) | Pure JavaScript |
| **Features** | Full SDK (sandboxes, tunnels, SSH) | Environments only |
| **Performance** | Native | HTTP |
| **Bundle Size** | ~15MB (with .so) | ~200KB |
| **Installation** | Requires build tools | npm install |
| **Use Case** | Server-side automation | Client-side apps |

Choose **Native Bindings** when:
- Running in Node.js server environment
- Need full sandbox management features
- Want feature parity with Python SDK
- Performance is important

Choose **HTTP Client** when:
- Running in browser
- Only need environment management
- Want minimal dependencies
- Bundle size matters

## Examples

See `examples/native-sandbox-usage.ts` for complete examples.

## Architecture

```
┌─────────────────────────────────────┐
│  TypeScript Application             │
└───────────────┬─────────────────────┘
                │
        ┌───────▼────────┐
        │  native-bindings.ts  │
        │  (TypeScript FFI)    │
        └───────┬────────┘
                │ ffi-napi
        ┌───────▼────────┐
        │  libplato.so    │
        │  (Go C shared)  │
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │  Go SDK         │
        │  plato-sdk/     │
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │  Plato API      │
        └─────────────────┘
```

## Troubleshooting

### Library Not Found

```bash
Error: Could not find libplato shared library
```

**Solution:** Build the shared library:

```bash
./scripts/build-typescript-bindings.sh
```

### FFI Installation Issues

```bash
npm ERR! gyp ERR! build error
```

**Solution:** Install build tools:

- **macOS**: `xcode-select --install`
- **Linux**: `sudo apt-get install build-essential`
- **Windows**: Install Visual Studio Build Tools

### Import Errors

```typescript
Cannot find module 'plato-sdk/native'
```

**Solution:** Ensure package is built and types are generated:

```bash
cd javascript
npm run build
```

## Development

```bash
# Build shared library and TypeScript
./scripts/build-typescript-bindings.sh

# Run examples
cd javascript
npm run examples examples/native-sandbox-usage.ts

# Run tests
npm test

# Lint
npm run lint
```

## Contributing

Contributions are welcome! Please see the main repository for guidelines.

## License

MIT

## Support

- 📖 [Documentation](https://plato.so/docs)
- 💬 [Discord](https://discord.gg/plato)
- 🐛 [Issues](https://github.com/plato-ai/plato-client/issues)

