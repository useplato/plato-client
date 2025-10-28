/**
 * Native TypeScript bindings for Plato Sandbox SDK
 * 
 * This module provides TypeScript bindings to the Go SDK via C FFI,
 * using the same shared library as the Python SDK.
 */

import ffi from 'ffi-napi';
import ref from 'ref-napi';
import path from 'path';
import { existsSync } from 'fs';
import type { components } from '../generated/types';

// Re-export auto-generated types from OpenAPI
export type SimConfigCompute = components['schemas']['SimConfigCompute'];
export type SimConfigMetadata = components['schemas']['SimConfigMetadata'];
export type SimConfigDataset = components['schemas']['SimConfigDataset'];
export type SimConfigService = components['schemas']['SimConfigService'];
export type SimConfigListener = components['schemas']['SimConfigListener'];
export type Sandbox = components['schemas']['Sandbox'];
export type CreateSnapshotRequest = components['schemas']['CreateSnapshotRequest'];
export type CreateSnapshotResponse = components['schemas']['CreateSnapshotResponse'];
export type StartWorkerRequest = components['schemas']['StartWorkerRequest'];
export type StartWorkerResponse = components['schemas']['StartWorkerResponse'];
export type SimulatorListItem = components['schemas']['SimulatorListItem'];
export type Variable = components['schemas']['Variable'];

// Custom types not in OpenAPI spec (API responses that aren't modeled)

export interface GiteaCredentials {
  username: string;
  password: string;
  org_name: string;
}

export interface GiteaRepository {
  name: string;
  clone_url: string;
  ssh_url: string;
  html_url?: string;
}

export interface ProxyTunnelInfo {
  tunnel_id: string;
  local_port: number;
}

export interface SSHInfo {
  ssh_command: string;
  ssh_host: string;
  ssh_config_path: string;
  public_key: string;
  private_key_path: string;
  public_id: string;
  correlation_id: string;
}

/**
 * Find the libplato shared library
 */
function findLibrary(): string {
  const extensions = process.platform === 'darwin' ? ['.dylib'] 
                   : process.platform === 'win32' ? ['.dll'] 
                   : ['.so'];

  // Try package directory first (for npm installs)
  const packageDir = __dirname;
  for (const ext of extensions) {
    const libPath = path.join(packageDir, `libplato${ext}`);
    if (existsSync(libPath)) {
      return libPath;
    }
  }

  // Try development location (sdk/bindings/c)
  const devPath = path.resolve(__dirname, '../../../sdk/bindings/c');
  for (const ext of extensions) {
    const libPath = path.join(devPath, `libplato${ext}`);
    if (existsSync(libPath)) {
      return libPath;
    }
  }

  throw new Error(
    `Could not find libplato shared library. Searched in:\n` +
    `  1. Package directory: ${packageDir}\n` +
    `  2. Development directory: ${devPath}\n` +
    `Run: ./scripts/build-typescript-bindings.sh`
  );
}

// Load the shared library
let lib: any;
let libPath: string;

function getLib() {
  if (!lib) {
    libPath = findLibrary();
    
    lib = ffi.Library(libPath, {
      'plato_new_client': ['pointer', ['string', 'string']],
      'plato_create_sandbox': ['pointer', ['string', 'string', 'string', 'string', 'string', 'string']],
      'plato_delete_sandbox': ['pointer', ['string', 'string']],
      'plato_create_snapshot': ['pointer', ['string', 'string', 'string']],
      'plato_start_worker': ['pointer', ['string', 'string', 'string']],
      'plato_list_simulators': ['pointer', ['string']],
      'plato_get_simulator_versions': ['pointer', ['string', 'string']],
      'plato_monitor_operation': ['pointer', ['string', 'string', 'int']],
      'plato_gitea_get_credentials': ['pointer', ['string']],
      'plato_gitea_list_simulators': ['pointer', ['string']],
      'plato_gitea_get_simulator_repo': ['pointer', ['string', 'int']],
      'plato_gitea_create_simulator_repo': ['pointer', ['string', 'int']],
      'plato_proxytunnel_start': ['pointer', ['string', 'string', 'int', 'int']],
      'plato_proxytunnel_stop': ['pointer', ['string', 'string']],
      'plato_proxytunnel_list': ['pointer', ['string']],
      'plato_gitea_push_to_hub': ['pointer', ['string', 'string', 'string']],
      'plato_gitea_merge_to_main': ['pointer', ['string', 'string', 'string']],
      'plato_setup_ssh': ['pointer', ['string', 'string', 'int', 'string', 'string', 'string', 'string']],
      'plato_free_string': ['void', ['pointer']],
    });
  }
  
  return lib;
}

/**
 * Helper to call C function and free the returned string
 */
function callAndFree(resultPtr: any): string {
  if (resultPtr.isNull()) {
    throw new Error('Got null pointer from C function');
  }
  
  try {
    const result = ref.readCString(resultPtr, 0);
    if (!result) {
      throw new Error('Got null string from C function');
    }
    return result;
  } finally {
    getLib().plato_free_string(resultPtr);
  }
}

/**
 * Plato Sandbox SDK Client for Node.js
 * 
 * TypeScript wrapper around the Go SDK via C FFI, providing the same
 * functionality as the Python SDK.
 * 
 * @example
 * ```typescript
 * import { PlatoSandboxClient } from 'plato-sdk/native';
 * 
 * const client = new PlatoSandboxClient('your-api-key');
 * 
 * // Create sandbox from artifact (waits by default)
 * const sandbox = await client.createSandbox({ artifactId: 'art_123' });
 * console.log(`Sandbox ready at ${sandbox.url}`);
 * 
 * // Close when done
 * await client.closeSandbox(sandbox.public_id);
 * ```
 */
export class PlatoSandboxClient {
  private clientId: string;
  private baseUrl: string;
  private sandboxConfigs: Map<string, { config: SimConfigDataset; dataset: string }> = new Map();

  /**
   * Initialize the Plato Sandbox client
   * 
   * @param apiKey - Your Plato API key
   * @param baseUrl - Base URL of the Plato API (default: 'https://plato.so/api')
   */
  constructor(apiKey: string, baseUrl: string = 'https://plato.so/api') {
    // Detect if user passed URL as api_key (old signature)
    if (apiKey.startsWith('http://') || apiKey.startsWith('https://')) {
      throw new Error(
        "It looks like you passed a URL as the api_key. " +
        "The signature is: PlatoSandboxClient(apiKey, baseUrl). " +
        `Did you mean: PlatoSandboxClient('${baseUrl}', '${apiKey}')?`
      );
    }

    this.baseUrl = baseUrl;
    
    const lib = getLib();
    const resultPtr = lib.plato_new_client(baseUrl, apiKey);
    this.clientId = callAndFree(resultPtr);
    
    console.log(`[PLATO-TS] Created PlatoSandboxClient with client_id=${this.clientId}`);
  }

  /**
   * Create a new VM sandbox
   * 
   * @param options - Sandbox creation options
   * @param options.config - Sandbox configuration (required if no artifactId)
   * @param options.dataset - Dataset name (default: 'base')
   * @param options.alias - Human-readable alias (default: 'sandbox')
   * @param options.artifactId - Optional artifact ID to launch from snapshot
   * @param options.service - Service name
   * @param options.wait - If true, blocks until sandbox is ready (default: true)
   * @param options.timeout - Timeout in seconds when wait=true (default: 600)
   * @returns Sandbox object
   */
  async createSandbox(options: {
    config?: SimConfigDataset;
    dataset?: string;
    alias?: string;
    artifactId?: string;
    service?: string;
    wait?: boolean;
    timeout?: number;
  }): Promise<Sandbox> {
    const {
      config,
      dataset = 'base',
      alias = 'sandbox',
      artifactId,
      service = '',
      wait = true,
      timeout = 600,
    } = options;

    // Validation
    if (!config && !artifactId) {
      throw new Error(
        "Must provide either 'config' or 'artifactId'. " +
        "Use 'config' to create from configuration, or 'artifactId' to create from snapshot."
      );
    }

    // Use boilerplate config if only artifactId provided
    let configJson: string;
    if (!config && artifactId) {
      configJson = JSON.stringify({
        compute: {
          cpus: 1,
          memory: 512,
          disk: 10240,
          app_port: 8080,
          plato_messaging_port: 7000,
        },
        metadata: {
          name: 'Default',
        },
      });
    } else {
      configJson = JSON.stringify(config);
    }

    console.log(`[PLATO-TS] Creating sandbox: artifact_id=${artifactId}, service=${service}, dataset=${dataset}`);
    
    const lib = getLib();
    const resultPtr = lib.plato_create_sandbox(
      this.clientId,
      configJson,
      dataset,
      alias,
      artifactId || '',
      service
    );

    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      console.error(`[PLATO-TS] Failed to create sandbox: ${response.error}`);
      throw new Error(`Failed to create sandbox: ${response.error}`);
    }

    const sandbox: Sandbox = response;
    console.log(`[PLATO-TS] Sandbox created: public_id=${sandbox.public_id}, job_group_id=${sandbox.job_group_id}`);
    console.log(`[PLATO-TS] Automatic heartbeat started for job_group_id=${sandbox.job_group_id}`);

    // Cache config for later use (e.g., in setupSSH)
    if (config) {
      this.sandboxConfigs.set(sandbox.public_id, { config, dataset });
    }

    // Wait for sandbox to be ready if requested
    if (wait && sandbox.correlation_id) {
      console.log(`[PLATO-TS] Waiting for sandbox ${sandbox.public_id} to be ready (timeout=${timeout}s)`);
      await this.waitUntilReady(sandbox.correlation_id, timeout);
      sandbox.status = 'running';
      console.log(`[PLATO-TS] Sandbox ${sandbox.public_id} is ready`);
    }

    return sandbox;
  }

  /**
   * Close a VM sandbox
   * 
   * @param publicId - Public ID of the sandbox to close
   */
  async closeSandbox(publicId: string): Promise<void> {
    console.log(`[PLATO-TS] Closing sandbox: public_id=${publicId}`);
    
    const lib = getLib();
    const resultPtr = lib.plato_delete_sandbox(this.clientId, publicId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      console.error(`[PLATO-TS] Failed to close sandbox ${publicId}: ${response.error}`);
      throw new Error(`Failed to close sandbox: ${response.error}`);
    }

    // Clean up cached config
    this.sandboxConfigs.delete(publicId);

    console.log(`[PLATO-TS] Sandbox ${publicId} closed successfully (heartbeat stopped automatically)`);
  }

  /**
   * Create a snapshot of a sandbox
   */
  async createSnapshot(publicId: string, request: CreateSnapshotRequest): Promise<CreateSnapshotResponse> {
    const requestJson = JSON.stringify(request);
    
    const lib = getLib();
    const resultPtr = lib.plato_create_snapshot(this.clientId, publicId, requestJson);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to create snapshot: ${response.error}`);
    }

    return response;
  }

  /**
   * Start a Plato worker in a sandbox
   */
  async startWorker(publicId: string, request: StartWorkerRequest): Promise<StartWorkerResponse> {
    const requestJson = JSON.stringify(request);
    
    const lib = getLib();
    const resultPtr = lib.plato_start_worker(this.clientId, publicId, requestJson);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to start worker: ${response.error}`);
    }

    return response;
  }

  /**
   * List all available simulators
   */
  async listSimulators(): Promise<SimulatorListItem[]> {
    const lib = getLib();
    const resultPtr = lib.plato_list_simulators(this.clientId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to list simulators: ${response.error}`);
    }

    return response;
  }

  /**
   * Get all versions for a specific simulator
   */
  async getSimulatorVersions(simulatorName: string): Promise<any[]> {
    const lib = getLib();
    const resultPtr = lib.plato_get_simulator_versions(this.clientId, simulatorName);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to get versions: ${response.error}`);
    }

    return response;
  }

  /**
   * Wait until an operation completes by monitoring SSE events
   * 
   * This function blocks until the operation completes or times out.
   */
  async waitUntilReady(correlationId: string, timeout: number = 600): Promise<void> {
    const lib = getLib();
    const resultPtr = lib.plato_monitor_operation(this.clientId, correlationId, timeout);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Operation failed: ${response.error}`);
    }
  }

  /**
   * Get Gitea credentials for the organization
   */
  async getGiteaCredentials(): Promise<GiteaCredentials> {
    const lib = getLib();
    const resultPtr = lib.plato_gitea_get_credentials(this.clientId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to get credentials: ${response.error}`);
    }

    return response;
  }

  /**
   * List all simulators with Gitea repository information
   */
  async listGiteaSimulators(): Promise<any[]> {
    const lib = getLib();
    const resultPtr = lib.plato_gitea_list_simulators(this.clientId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to list simulators: ${response.error}`);
    }

    return response;
  }

  /**
   * Get repository information for a simulator
   */
  async getGiteaRepository(simulatorId: number): Promise<GiteaRepository> {
    const lib = getLib();
    const resultPtr = lib.plato_gitea_get_simulator_repo(this.clientId, simulatorId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to get repository: ${response.error}`);
    }

    return response;
  }

  /**
   * Create a repository for a simulator
   */
  async createGiteaRepository(simulatorId: number): Promise<GiteaRepository> {
    const lib = getLib();
    const resultPtr = lib.plato_gitea_create_simulator_repo(this.clientId, simulatorId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to create repository: ${response.error}`);
    }

    return response;
  }

  /**
   * Start a proxy tunnel to connect to a port on the sandbox
   */
  async startProxyTunnel(publicId: string, remotePort: number, localPort: number = 0): Promise<ProxyTunnelInfo> {
    console.log(`[PLATO-TS] Starting proxy tunnel: public_id=${publicId}, remote_port=${remotePort}, local_port=${localPort}`);
    
    const lib = getLib();
    const resultPtr = lib.plato_proxytunnel_start(this.clientId, publicId, remotePort, localPort);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to start proxy tunnel: ${response.error}`);
    }

    console.log(`[PLATO-TS] Proxy tunnel started: tunnel_id=${response.tunnel_id}, local_port=${response.local_port}`);
    return response;
  }

  /**
   * Stop a running proxy tunnel
   */
  async stopProxyTunnel(tunnelId: string): Promise<void> {
    console.log(`[PLATO-TS] Stopping proxy tunnel: tunnel_id=${tunnelId}`);
    
    const lib = getLib();
    const resultPtr = lib.plato_proxytunnel_stop(this.clientId, tunnelId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to stop proxy tunnel: ${response.error}`);
    }

    console.log(`[PLATO-TS] Proxy tunnel stopped: tunnel_id=${tunnelId}`);
  }

  /**
   * List all active proxy tunnels
   */
  async listProxyTunnels(): Promise<any[]> {
    const lib = getLib();
    const resultPtr = lib.plato_proxytunnel_list(this.clientId);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to list proxy tunnels: ${response.error}`);
    }

    return response;
  }

  /**
   * Push local code to Gitea repository on a timestamped branch
   */
  async pushToGitea(serviceName: string, sourceDir: string = ''): Promise<any> {
    console.log(`[PLATO-TS] Pushing to Gitea: service=${serviceName}, source_dir=${sourceDir}`);
    
    const lib = getLib();
    const resultPtr = lib.plato_gitea_push_to_hub(this.clientId, serviceName, sourceDir);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to push to Gitea: ${response.error}`);
    }

    console.log(`[PLATO-TS] Pushed to Gitea: branch=${response.BranchName}`);
    return response;
  }

  /**
   * Merge a workspace branch to main and return the git hash
   */
  async mergeToMain(serviceName: string, branchName: string): Promise<string> {
    console.log(`[PLATO-TS] Merging to main: service=${serviceName}, branch=${branchName}`);
    
    const lib = getLib();
    const resultPtr = lib.plato_gitea_merge_to_main(this.clientId, serviceName, branchName);
    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to merge to main: ${response.error}`);
    }

    const gitHash = response.git_hash;
    console.log(`[PLATO-TS] Merged to main: git_hash=${gitHash}`);
    return gitHash;
  }

  /**
   * Setup SSH configuration for a sandbox
   */
  async setupSSH(
    sandbox: Sandbox,
    options?: {
      config?: SimConfigDataset;
      dataset?: string;
      localPort?: number;
      username?: string;
    }
  ): Promise<SSHInfo> {
    const { config, dataset, localPort = 2200, username = 'plato' } = options || {};

    console.log(`[PLATO-TS] Setting up SSH for sandbox ${sandbox.public_id}`);

    // Try to get cached config if not provided
    let finalConfig = config;
    let finalDataset = dataset;

    if (!finalConfig) {
      const cached = this.sandboxConfigs.get(sandbox.public_id);
      if (!cached) {
        throw new Error(
          `No cached config found for sandbox ${sandbox.public_id}. ` +
          'Please provide config and dataset explicitly.'
        );
      }
      finalConfig = cached.config;
      if (!finalDataset) {
        finalDataset = cached.dataset;
      }
    }

    if (!finalDataset) {
      finalDataset = 'base';
    }

    const configJson = JSON.stringify(finalConfig);

    const lib = getLib();
    const resultPtr = lib.plato_setup_ssh(
      this.clientId,
      this.baseUrl,
      localPort,
      sandbox.public_id,
      username,
      configJson,
      finalDataset
    );

    const resultStr = callAndFree(resultPtr);
    const response = JSON.parse(resultStr);

    if (response.error) {
      throw new Error(`Failed to setup SSH: ${response.error}`);
    }

    console.log(`[PLATO-TS] SSH setup complete for ${sandbox.public_id}: ${response.ssh_command}`);
    return response;
  }
}

