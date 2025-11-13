/**
 * Server-Sent Event (SSE) from the operation monitoring stream.
 */
export interface OperationEvent {
    /** Event type */
    type: 'connected' | 'progress' | 'complete' | 'error' | string;
    
    /** Whether the operation succeeded */
    success?: boolean;
    
    /** Human-readable message */
    message?: string;
    
    /** Error details if the operation failed */
    error?: string;
}

/**
 * Custom errors for operation monitoring.
 */
export class OperationTimeoutError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'OperationTimeoutError';
    }
}

export class OperationFailedError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'OperationFailedError';
    }
}

