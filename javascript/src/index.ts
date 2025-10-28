/**
 * Plato SDK for TypeScript/JavaScript
 * 
 * Two APIs available:
 * 
 * 1. HTTP Client (Browser + Node.js) - Environment management
 *    import { Plato, PlatoEnvironment } from 'plato-sdk';
 * 
 * 2. Native Bindings (Node.js only) - Full sandbox SDK
 *    import { PlatoSandboxClient } from 'plato-sdk/native';
 */

// HTTP Client (works in browser and Node.js)
export { Plato, PlatoEnvironment, PlatoTask } from './plato/client';
export { PlatoClientError } from './plato/exceptions';
export { Config } from './plato/config';

// Native Bindings (Node.js only - full sandbox SDK)
// Import from 'plato-sdk/native'
export { PlatoSandboxClient } from './plato/native-bindings';
export type {
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
} from './plato/native-bindings';
