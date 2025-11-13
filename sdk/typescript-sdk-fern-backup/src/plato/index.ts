/**
 * Plato SDK - TypeScript Client
 * 
 * This module exports the PlatoClient wrapper which extends the auto-generated
 * Fern SDK with additional helper methods for heartbeat management and SSE monitoring.
 */

// Export the wrapper client
export { PlatoClient, type PlatoClientOptions } from './client.js';

// Export custom types and errors
export { 
    OperationEvent, 
    OperationTimeoutError, 
    OperationFailedError 
} from './types.js';

// Re-export all generated types and APIs for convenience
export * from './_generated/index.js';

