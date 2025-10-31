# Reference
<details><summary><code>client.MakeEnvironment(request) -> *sdk.MakeEnvironmentResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.MakeEnvironmentRequest{
        InterfaceType: "interface_type",
        EnvId: "env_id",
    }
client.MakeEnvironment(
        context.TODO(),
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**interfaceType:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**interfaceWidth:** `*int` 
    
</dd>
</dl>

<dl>
<dd>

**interfaceHeight:** `*int` 
    
</dd>
</dl>

<dl>
<dd>

**source:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**openPageOnStart:** `*bool` 
    
</dd>
</dl>

<dl>
<dd>

**envId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**tag:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**dataset:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**artifactId:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**envConfig:** `map[string]any` 
    
</dd>
</dl>

<dl>
<dd>

**recordNetworkRequests:** `*bool` 
    
</dd>
</dl>

<dl>
<dd>

**recordActions:** `*bool` 
    
</dd>
</dl>

<dl>
<dd>

**keepalive:** `*bool` 
    
</dd>
</dl>

<dl>
<dd>

**alias:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**fast:** `*bool` 
    
</dd>
</dl>

<dl>
<dd>

**version:** `*string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetJobStatus(JobId) -> *sdk.JobStatusResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.GetJobStatus(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetCdpUrl(JobId) -> *sdk.CdpUrlResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.GetCdpUrl(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetProxyUrl(JobId) -> *sdk.ProxyUrlResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.GetProxyUrl(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.CloseEnvironment(JobId) -> *sdk.CloseEnvironmentResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.CloseEnvironment(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.BackupEnvironment(JobId) -> *sdk.BackupEnvironmentResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.BackupEnvironment(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.ResetEnvironment(JobId, request) -> *sdk.ResetEnvironmentResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.ResetEnvironmentRequest{}
client.ResetEnvironment(
        context.TODO(),
        "job_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**testCasePublicId:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**agentVersion:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**loadBrowserState:** `*bool` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetEnvironmentState(JobId) -> *sdk.EnvironmentStateResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.GetEnvironmentStateRequest{
        MergeMutations: sdk.Bool(
            true,
        ),
    }
client.GetEnvironmentState(
        context.TODO(),
        "job_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**mergeMutations:** `*bool` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetWorkerReady(JobId) -> *sdk.WorkerReadyResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.GetWorkerReady(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.SendHeartbeat(JobId) -> *sdk.HeartbeatResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.SendHeartbeat(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetActiveSession(JobId) -> *sdk.ActiveSessionResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.GetActiveSession(
        context.TODO(),
        "job_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.EvaluateSession(SessionId, request) -> *sdk.EvaluateResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.EvaluateRequest{}
client.EvaluateSession(
        context.TODO(),
        "session_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**sessionId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**value:** `map[string]any` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.PostEvaluationResult(SessionId, request) -> *sdk.PostEvaluationResultResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.PostEvaluationResultRequest{
        Success: true,
    }
client.PostEvaluationResult(
        context.TODO(),
        "session_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**sessionId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**success:** `bool` 
    
</dd>
</dl>

<dl>
<dd>

**reason:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**agentVersion:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**mutations:** `[]map[string]any` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.LogMessage(SessionId, request) -> *sdk.LogResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.LogRequest{
        Source: "source",
        Type: "type",
        Message: map[string]any{
            "key": "value",
        },
        Timestamp: "timestamp",
    }
client.LogMessage(
        context.TODO(),
        "session_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**sessionId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**source:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**type_:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**message:** `map[string]any` 
    
</dd>
</dl>

<dl>
<dd>

**timestamp:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.ListSimulators() -> []*sdk.Simulator</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.ListSimulators(
        context.TODO(),
    )
}
```
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetTestCases() -> *sdk.TestCasesResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.GetTestCasesRequest{
        SimulatorName: sdk.String(
            "simulator_name",
        ),
        SimulatorId: sdk.String(
            "simulator_id",
        ),
        PageSize: sdk.Int(
            1,
        ),
    }
client.GetTestCases(
        context.TODO(),
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**simulatorName:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**simulatorId:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**pageSize:** `*int` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.GetRunningSessionsCount() -> *sdk.RunningSessionsCountResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.GetRunningSessionsCount(
        context.TODO(),
    )
}
```
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.MonitorOperation(CorrelationId) -> sdk.OperationEvent</code></summary>
<dl>
<dd>

#### 📝 Description

<dl>
<dd>

<dl>
<dd>

Monitor the progress of long-running operations (sandbox creation, setup, etc.) via SSE.

**Event Flow:**
1. First event: `type: "connected"` - Connection established, continue listening
2. Progress events: `type: "progress"` with `message` field - Operation updates
3. Completion: `type: "run_result"` or `"ssh_result"` - Operation finished
   - Check `success: true` for successful completion
   - Check `error` or `message` field if `success: false`
4. Error: `type: "error"` - Operation failed, check `error` or `message` field

**Data Format:**
SSE data is base64-encoded JSON. Decode it to get the OperationEvent object.

**Client Implementation Required:**
- Decode base64 data from each SSE event
- Parse JSON to OperationEvent
- Check event.type and event.success to determine operation status
- Continue listening until receiving a terminal event (run_result, ssh_result, or error)
- Return success/error based on the terminal event

**Example (pseudo-code):**
```
for event in stream:
  decoded = base64_decode(event.data)
  operation_event = json_parse(decoded)
  
  if operation_event.type == "connected":
    continue  # Keep listening
  elif operation_event.type in ["run_result", "ssh_result"]:
    if operation_event.success:
      return SUCCESS
    else:
      return ERROR(operation_event.error || operation_event.message)
  elif operation_event.type == "error":
    return ERROR(operation_event.error || operation_event.message)
```
</dd>
</dl>
</dd>
</dl>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.MonitorOperation(
        context.TODO(),
        "correlation_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**correlationId:** `string` — Correlation ID from sandbox creation or setup operation
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.CreateSandbox(request) -> *sdk.CreateSandboxResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.CreateSandboxRequest{
        Dataset: "dataset",
        PlatoDatasetConfig: &sdk.SimConfigDataset{
            Compute: &sdk.SimConfigCompute{
                Cpus: 1,
                Memory: 1,
                Disk: 1,
                AppPort: 1,
                PlatoMessagingPort: 1,
            },
            Metadata: &sdk.SimConfigMetadata{
                Name: "name",
            },
        },
    }
client.CreateSandbox(
        context.TODO(),
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**dataset:** `string` — Dataset name (e.g., "base")
    
</dd>
</dl>

<dl>
<dd>

**platoDatasetConfig:** `*sdk.SimConfigDataset` 
    
</dd>
</dl>

<dl>
<dd>

**timeout:** `*int` — Timeout in seconds for sandbox creation
    
</dd>
</dl>

<dl>
<dd>

**waitTime:** `*int` — Wait time in seconds
    
</dd>
</dl>

<dl>
<dd>

**alias:** `*string` — Human-readable alias for the sandbox
    
</dd>
</dl>

<dl>
<dd>

**artifactId:** `*string` — Optional artifact ID to create sandbox from snapshot
    
</dd>
</dl>

<dl>
<dd>

**service:** `*string` — Service name
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.SetupSandbox(JobId, request) -> *sdk.SetupSandboxResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.SetupSandboxRequest{
        Dataset: "dataset",
        PlatoDatasetConfig: &sdk.SimConfigDataset{
            Compute: &sdk.SimConfigCompute{
                Cpus: 1,
                Memory: 1,
                Disk: 1,
                AppPort: 1,
                PlatoMessagingPort: 1,
            },
            Metadata: &sdk.SimConfigMetadata{
                Name: "name",
            },
        },
    }
client.SetupSandbox(
        context.TODO(),
        "job_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**jobId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**dataset:** `string` — Dataset name
    
</dd>
</dl>

<dl>
<dd>

**platoDatasetConfig:** `*sdk.SimConfigDataset` 
    
</dd>
</dl>

<dl>
<dd>

**sshPublicKey:** `*string` — SSH public key to install for plato user
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.DeleteSandbox(PublicId) -> *sdk.DeleteSandboxResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
client.DeleteSandbox(
        context.TODO(),
        "public_id",
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**publicId:** `string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.CreateSnapshot(PublicId, request) -> *sdk.CreateSnapshotResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.CreateSnapshotRequest{}
client.CreateSnapshot(
        context.TODO(),
        "public_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**publicId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**service:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**gitHash:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**dataset:** `*string` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.StartWorker(PublicId, request) -> *sdk.StartWorkerResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.StartWorkerRequest{
        Dataset: "dataset",
        PlatoDatasetConfig: &sdk.SimConfigDataset{
            Compute: &sdk.SimConfigCompute{
                Cpus: 1,
                Memory: 1,
                Disk: 1,
                AppPort: 1,
                PlatoMessagingPort: 1,
            },
            Metadata: &sdk.SimConfigMetadata{
                Name: "name",
            },
        },
    }
client.StartWorker(
        context.TODO(),
        "public_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**publicId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**service:** `*string` 
    
</dd>
</dl>

<dl>
<dd>

**dataset:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**platoDatasetConfig:** `*sdk.SimConfigDataset` 
    
</dd>
</dl>

<dl>
<dd>

**timeout:** `*int` 
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>

<details><summary><code>client.SetupRootAccess(PublicId, request) -> *sdk.SetupRootAccessResponse</code></summary>
<dl>
<dd>

#### 🔌 Usage

<dl>
<dd>

<dl>
<dd>

```go
request := &sdk.SetupRootAccessRequest{
        SshPublicKey: "ssh_public_key",
    }
client.SetupRootAccess(
        context.TODO(),
        "public_id",
        request,
    )
}
```
</dd>
</dl>
</dd>
</dl>

#### ⚙️ Parameters

<dl>
<dd>

<dl>
<dd>

**publicId:** `string` 
    
</dd>
</dl>

<dl>
<dd>

**sshPublicKey:** `string` — SSH public key to install for root user
    
</dd>
</dl>

<dl>
<dd>

**timeout:** `*int` — Timeout in seconds
    
</dd>
</dl>
</dd>
</dl>


</dd>
</dl>
</details>
