/**
 * Test that generated types work correctly
 */

import type { components } from './src/generated/types';

// Test type extraction
type SimConfigDataset = components['schemas']['SimConfigDataset'];
type Sandbox = components['schemas']['Sandbox'];
type CreateSnapshotRequest = components['schemas']['CreateSnapshotRequest'];

// Test usage
const config: SimConfigDataset = {
  compute: {
    cpus: 2,
    memory: 1024,
    disk: 20480,
    app_port: 8080,
    plato_messaging_port: 7000,
  },
  metadata: {
    name: 'Test Sandbox',
    description: 'A test sandbox',
  },
};

const sandbox: Sandbox = {
  public_id: 'sandbox-123',
  job_group_id: 'job-group-456',
  job_id: 'job-789',
  status: 'running',
  url: 'https://example.com',
  correlation_id: 'corr-abc',
};

const snapshotReq: CreateSnapshotRequest = {
  service: 'web',
  dataset: 'base',
  git_hash: 'abc123',
};

console.log('✅ All types compile successfully!');
console.log('Config:', config.metadata.name);
console.log('Sandbox:', sandbox.public_id);
console.log('Snapshot request:', snapshotReq.service);

