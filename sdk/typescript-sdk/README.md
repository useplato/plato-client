# @plato-ai/sdk

TypeScript SDK for interacting with the Plato platform. Manage environments, VMs, simulators, and more with automatic heartbeat management and SSE streaming support.

## Installation

```bash
npm install @plato-ai/sdk
```

## Quick Start

```typescript
import { PlatoClient } from '@plato-ai/sdk';

// Initialize the client with your API key
const client = new PlatoClient({
    apiKey: 'your-api-key-here',
    basePath: 'https://your-plato-instance.com', // optional
});

// The client automatically manages heartbeats for all environments and VMs
```

## Usage Examples

### Environment Management

```typescript
// Create an environment (heartbeat starts automatically)
const env = await client.makeEnvironment({
    service: 'my-simulator',
    version: 'v1.0.0',
    // ... other options
});

console.log('Environment created:', env.job_group_id);

// Get environment status
const status = await client.env.getJobStatusApiEnvJobGroupIdStatusGet({
    jobGroupId: env.job_group_id
});

// Close environment (heartbeat stops automatically)
await client.closeEnvironment(env.job_group_id);
```

### Sandbox VM Management with Operation Monitoring

```typescript
// Create a sandbox VM (heartbeat starts automatically)
const vm = await client.createSandbox({
    vCpus: 4,
    memoryGb: 16,
    // ... other options
});

console.log('VM created, correlation ID:', vm.correlationId);

// Monitor the setup operation via SSE
try {
    const result = await client.monitorOperationSync(
        vm.correlationId,
        300000 // 5 minute timeout
    );
    console.log('VM setup complete:', result.message);
} catch (error) {
    if (error instanceof OperationTimeoutError) {
        console.error('VM setup timed out');
    } else if (error instanceof OperationFailedError) {
        console.error('VM setup failed:', error.message);
    }
}

// Setup sandbox on the VM
const setupResult = await client.publicBuild.setupSandboxApiPublicBuildVmPublicIdSetupSandboxPost({
    publicId: vm.publicId,
    setupSandboxRequest: {
        // ... setup options
    }
});

// Monitor sandbox setup
await client.monitorOperationSync(setupResult.correlationId);

// Close VM (heartbeat stops automatically)
await client.closeVM(vm.publicId);
```

### Complete Environment Lifecycle Example

Here's a complete example showing the typical workflow:

```typescript
import { PlatoClient } from '@plato-ai/sdk';

const client = new PlatoClient({
    apiKey: process.env.PLATO_API_KEY!,
    basePath: process.env.PLATO_BASE_URL || 'https://api.plato.so',
});

async function runEnvironmentLifecycle() {
    // 1. Create environment with automatic heartbeat
    const env = await client.makeEnvironment({
        service: 'espocrm',
        version: 'latest',
        fast: true,
        recordNetworkRequests: true,
        artifactId: '2ea954c0-7e5a-4a12-82fd-12cb46538827',
    });

    console.log('Environment created:', env.jobId);

    // 2. Wait for environment to be ready
    await client.waitForEnvironmentReady(env.jobId);
    console.log('Environment ready!');

    // 3. Reset environment with a task
    await client.env.resetEnvApiEnvJobGroupIdResetPost({
        jobGroupId: env.jobId,
        resetEnvRequest: {
            taskId: '1a84e3d6-1900-40ba-bf00-beeca1748ad5',
        },
    });

    // 4. Get environment URLs
    const publicUrl = await client.env.getProxyUrlApiEnvJobGroupIdProxyUrlGet({ 
        jobGroupId: env.jobId 
    });
    console.log('Public URL:', publicUrl);

    const cdpUrl = await client.env.getCdpUrlApiEnvJobGroupIdCdpUrlGet({ 
        jobGroupId: env.jobId 
    });
    console.log('CDP URL:', cdpUrl);

    // 5. Get environment state
    const state = await client.env.getEnvStateApiEnvJobGroupIdStateGet({ 
        jobGroupId: env.jobId 
    });
    console.log('Environment state:', state);

    // 6. Get active session
    const session = await client.env.getActiveSessionApiEnvJobGroupIdActiveSessionGet({ 
        jobGroupId: env.jobId 
    });
    const sessionId = (session as any).session_id;

    // 7. Evaluate the session
    const evaluation = await client.env.evaluateSessionApiEnvSessionSessionIdEvaluatePost({
        sessionId,
        evaluateRequest: {
            // Custom evaluation data
            customData: { test: true },
        },
    });
    console.log('Evaluation result:', evaluation);

    // 8. Score the session
    await client.env.scoreSessionApiEnvSessionSessionIdScorePost({
        sessionId,
        scoreRequest: {
            score: 0.95,
            metadata: {
                reasoning: 'Task completed successfully',
            },
        },
    });

    // 9. Close environment (heartbeat stops automatically)
    await client.closeEnvironment(env.jobId);
    console.log('Environment closed');
}

runEnvironmentLifecycle().catch(console.error);
```

### Environment State Management

```typescript
// Get current state
const state = await client.env.getEnvStateApiEnvJobGroupIdStateGet({
    jobGroupId: 'job-123'
});

// Reset to a specific task
await client.env.resetEnvApiEnvJobGroupIdResetPost({
    jobGroupId: 'job-123',
    resetEnvRequest: {
        taskId: 'task-456',
        // Optional: specify reset behavior
        resetType: 'hard', // or 'soft'
    }
});

// Backup current state
await client.env.backupEnvApiEnvJobGroupIdBackupPost({
    jobGroupId: 'job-123'
});
```

### Session Management

```typescript
// Get active session
const session = await client.env.getActiveSessionApiEnvJobGroupIdActiveSessionGet({
    jobGroupId: 'job-123'
});

// Evaluate session
const evaluation = await client.env.evaluateSessionApiEnvSessionSessionIdEvaluatePost({
    sessionId: session.session_id,
    evaluateRequest: {
        customData: { /* your evaluation data */ }
    }
});

// Score session
await client.env.scoreSessionApiEnvSessionSessionIdScorePost({
    sessionId: session.session_id,
    scoreRequest: {
        score: 0.85,
        metadata: {
            reasoning: 'Good performance',
            metrics: { accuracy: 0.9, speed: 0.8 }
        }
    }
});

// Log session data
await client.env.logApiEnvSessionIdLogPost({
    sessionId: session.session_id,
    log: {
        level: 'info',
        message: 'Task step completed',
        data: { step: 1, action: 'click' }
    }
});
```

### Simulator Management

```typescript
// List available simulators
const simulators = await client.env.listSimulatorsApiEnvSimulatorsGet({});

// Get simulator versions
const versions = await client.simulator.getSimulatorVersionsApiSimulatorSimulatorNameVersionsGet({
    simulatorName: 'espocrm'
});

console.log('Available versions:', versions.versions);

// Get database configuration for a simulator
const dbConfig = await client.simulator.getDbConfigApiSimulatorArtifactIdDbConfigGetRaw({
    artifactId: '2ea954c0-7e5a-4a12-82fd-12cb46538827'
});

// Create a new simulator
await client.env.createSimulatorApiEnvSimulatorsPost({
    createSimulatorRequest: {
        name: 'my-simulator',
        description: 'Custom simulator',
        baseImage: 'ubuntu:22.04'
    }
});
```

### Gitea Repository Management

```typescript
// Get your Gitea info
const myInfo = await client.gitea.getMyInfoApiGiteaMyInfoGet({});
console.log('Gitea user:', myInfo);

// List simulator repositories
const repos = await client.gitea.listSimulatorsApiGiteaSimulatorsGet({});

// Get repository info for a specific simulator
const repoInfo = await client.gitea.getRepoInfoApiGiteaSimulatorsSimulatorIdRepoGet({
    simulatorId: 'sim-123'
});

console.log('Repository:', repoInfo.url);

// Get Gitea credentials (for cloning repos)
const credentials = await client.gitea.getCredentialsApiGiteaCredentialsGet({});
console.log('Git credentials:', credentials);

// Create a repository for a simulator
await client.gitea.createRepoApiGiteaSimulatorsSimulatorIdRepoPost({
    simulatorId: 'sim-123',
    body: {
        name: 'my-simulator-repo',
        description: 'Simulator repository'
    }
});
```

### Getting Environment URLs

```typescript
// Get CDP (Chrome DevTools Protocol) URL for browser automation
const cdpUrl = await client.env.getCdpUrlApiEnvJobGroupIdCdpUrlGet({
    jobGroupId: 'job-123'
});

// Get proxy URL for accessing the application
const proxyUrl = await client.env.getProxyUrlApiEnvJobGroupIdProxyUrlGet({
    jobGroupId: 'job-123'
});

// Get public URL (if available)
// Note: This may require special permissions
console.log('CDP URL:', cdpUrl);
console.log('Proxy URL:', proxyUrl);
```

### SSE Event Streaming

```typescript
// Monitor any operation by correlation ID
const monitorOperation = async (correlationId: string) => {
    try {
        const result = await client.monitorOperationSync(correlationId, 600000); // 10 min timeout
        console.log('Operation completed:', result);
        return result;
    } catch (error) {
        if (error instanceof OperationTimeoutError) {
            console.error('Operation timed out after 10 minutes');
        } else if (error instanceof OperationFailedError) {
            console.error('Operation failed:', error.message);
        } else {
            console.error('Unexpected error:', error);
        }
        throw error;
    }
};
```

### Advanced Patterns

#### Reusing Environments Across Tasks

```typescript
// Create environment once
const env = await client.makeEnvironment({
    service: 'espocrm',
    version: 'latest',
});

await client.waitForEnvironmentReady(env.jobId);

// Run multiple tasks in the same environment
const tasks = ['task-1', 'task-2', 'task-3'];

for (const taskId of tasks) {
    // Reset to the task
    await client.env.resetEnvApiEnvJobGroupIdResetPost({
        jobGroupId: env.jobId,
        resetEnvRequest: { taskId },
    });
    
    // Get the session
    const session = await client.env.getActiveSessionApiEnvJobGroupIdActiveSessionGet({
        jobGroupId: env.jobId
    });
    
    // Your task logic here...
    // await performTask(session);
    
    // Evaluate and score
    await client.env.evaluateSessionApiEnvSessionSessionIdEvaluatePost({
        sessionId: (session as any).session_id,
    });
    
    await client.env.scoreSessionApiEnvSessionSessionIdScorePost({
        sessionId: (session as any).session_id,
        scoreRequest: { score: 1.0 },
    });
}

// Close when done with all tasks
await client.closeEnvironment(env.jobId);
```

#### Error Handling and Retry Logic

```typescript
async function createEnvironmentWithRetry(
    client: PlatoClient,
    request: MakeEnvRequest2,
    maxRetries: number = 3
) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const env = await client.makeEnvironment(request);
            
            // Wait with timeout
            await client.waitForEnvironmentReady(env.jobId, 2000, 300000);
            
            return env;
        } catch (error) {
            console.error(`Attempt ${i + 1} failed:`, error);
            
            if (i === maxRetries - 1) {
                throw error; // Last attempt failed
            }
            
            // Wait before retry
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }
}
```

#### Parallel Environment Management

```typescript
// Create multiple environments in parallel
const environments = await Promise.all([
    client.makeEnvironment({ service: 'espocrm', version: 'v1' }),
    client.makeEnvironment({ service: 'firefly', version: 'v2' }),
    client.makeEnvironment({ service: 'wordpress', version: 'v3' }),
]);

// Wait for all to be ready
await Promise.all(
    environments.map(env => 
        client.waitForEnvironmentReady(env.jobId)
    )
);

console.log('All environments ready!');

// Work with them...

// Close all when done
await Promise.all(
    environments.map(env => 
        client.closeEnvironment(env.jobId)
    )
);
```

### Cleanup

```typescript
// Stop all heartbeats when you're done
client.stopAllHeartbeats();

// Or use the destroy method
client.destroy();
```

## API Reference

### PlatoClient

Main client class with enhanced functionality.

#### Constructor Options

```typescript
interface PlatoClientOptions {
    apiKey: string;              // Required: Your Plato API key
    basePath?: string;           // Optional: API base URL (default: 'http://localhost')
    heartbeatInterval?: number;  // Optional: Heartbeat interval in ms (default: 30000)
}
```

#### Methods

- **`makeEnvironment(request)`** - Create environment with automatic heartbeat
- **`waitForEnvironmentReady(jobGroupId, pollInterval?, timeout?)`** - Wait for environment to be ready
- **`closeEnvironment(jobGroupId)`** - Close environment and stop heartbeat
- **`createSandbox(request)`** - Create sandbox VM with automatic heartbeat
- **`closeVM(publicId)`** - Close VM and stop heartbeat
- **`monitorOperationSync(correlationId, timeout?)`** - Monitor operation via SSE
- **`stopAllHeartbeats()`** - Stop all active heartbeats
- **`destroy()`** - Cleanup all resources

#### API Namespaces

- **`client.env`** - Environment management API
- **`client.publicBuild`** - VM and sandbox management API
- **`client.gitea`** - Gitea repository management API
- **`client.simulator`** - Simulator management API

## Error Handling

```typescript
import {
    PlatoClient,
    OperationTimeoutError,
    OperationFailedError
} from '@plato-ai/sdk';

try {
    await client.monitorOperationSync(correlationId);
} catch (error) {
    if (error instanceof OperationTimeoutError) {
        // Handle timeout
    } else if (error instanceof OperationFailedError) {
        // Handle operation failure
    } else {
        // Handle other errors
    }
}
```

## Flow Executor - Browser Automation

The SDK includes a powerful Flow Executor for browser automation using Playwright. This is particularly useful for testing simulator interactions.

### Installation

```bash
# Install Playwright (required for flow executor)
npm install playwright
```

### Basic Example

```typescript
import { chromium } from 'playwright';
import { FlowExecutor, Flow } from '@plato-ai/sdk';

async function runFlow() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  const flow: Flow = {
    name: 'login',
    description: 'Login to the application',
    steps: [
      {
        type: 'navigate',
        url: 'https://example.com/login',
        description: 'Navigate to login page'
      },
      {
        type: 'fill',
        selector: '#username',
        value: 'testuser',
        description: 'Fill username'
      },
      {
        type: 'fill',
        selector: '#password',
        value: 'password123',
        description: 'Fill password'
      },
      {
        type: 'click',
        selector: 'button[type="submit"]',
        description: 'Click login button'
      },
      {
        type: 'verify',
        verifyType: 'page_title',
        title: 'Dashboard',
        contains: true,
        description: 'Verify we are on the dashboard'
      },
      {
        type: 'screenshot',
        filename: 'dashboard.png',
        fullPage: true,
        description: 'Capture dashboard'
      }
    ]
  };

  const executor = new FlowExecutor({
    page,
    flow,
    screenshotsDir: './screenshots'
  });

  const success = await executor.executeFlow();
  await browser.close();
  
  return success;
}
```

### Available Step Types

- **Navigation**: `navigate`, `wait_for_url`
- **Interaction**: `click`, `fill`, `wait`, `wait_for_selector`
- **Verification**: `verify`, `verify_text`, `verify_url`, `verify_no_errors`, `check_element`
- **Utility**: `screenshot`

See the [Flow Executor README](./src/flow/README.md) for detailed documentation and more examples.

## Development

```bash
# Build the SDK
npm run build

# Clean build artifacts
npm run clean
```

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.
