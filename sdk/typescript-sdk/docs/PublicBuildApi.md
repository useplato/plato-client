# PublicBuildApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**checkpointVM**](PublicBuildApi.md#checkpointvm) | **POST** /public-build/vm/{public_id}/checkpoint | Checkpoint Vm |
| [**closeVM**](PublicBuildApi.md#closevm) | **DELETE** /public-build/vm/{public_id} | Close Vm |
| [**createVM**](PublicBuildApi.md#createvmoperation) | **POST** /public-build/vm/create | Create Vm |
| [**getOperationEvents**](PublicBuildApi.md#getoperationevents) | **GET** /public-build/events/{correlation_id} | Get Operation Events |
| [**saveVmSnapshotApiPublicBuildVmPublicIdSnapshotPost**](PublicBuildApi.md#savevmsnapshotapipublicbuildvmpublicidsnapshotpost) | **POST** /public-build/vm/{public_id}/snapshot | Save Vm Snapshot |
| [**setupRootAccessApiPublicBuildVmPublicIdSetupRootAccessPost**](PublicBuildApi.md#setuprootaccessapipublicbuildvmpublicidsetuprootaccesspost) | **POST** /public-build/vm/{public_id}/setup-root-access | Setup Root Access |
| [**setupSandbox**](PublicBuildApi.md#setupsandboxoperation) | **POST** /public-build/vm/{public_id}/setup-sandbox | Setup Sandbox |
| [**startWorker**](PublicBuildApi.md#startworker) | **POST** /public-build/vm/{public_id}/start-worker | Start Worker |



## checkpointVM

> CreateSnapshotResponse checkpointVM(publicId, createSnapshotRequest)

Checkpoint Vm

Create a checkpoint snapshot of a VM.  This creates a blockdiff_checkpoint artifact type instead of a regular blockdiff. Optional parameters allow overriding artifact labels: - service: Simulator name (defaults to job\&#39;s service) - git_hash: Git hash/version (defaults to job\&#39;s version or \&quot;unknown\&quot;) - dataset: Dataset name (defaults to job\&#39;s dataset) 

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { CheckpointVMRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // string
    publicId: publicId_example,
    // CreateSnapshotRequest (optional)
    createSnapshotRequest: ...,
  } satisfies CheckpointVMRequest;

  try {
    const data = await api.checkpointVM(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **publicId** | `string` |  | [Defaults to `undefined`] |
| **createSnapshotRequest** | [CreateSnapshotRequest](CreateSnapshotRequest.md) |  | [Optional] |

### Return type

[**CreateSnapshotResponse**](CreateSnapshotResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## closeVM

> VMManagementResponse closeVM(publicId)

Close Vm

Close and terminate a VM.

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { CloseVMRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // string
    publicId: publicId_example,
  } satisfies CloseVMRequest;

  try {
    const data = await api.closeVM(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **publicId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**VMManagementResponse**](VMManagementResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## createVM

> CreateVMResponse createVM(createVMRequest)

Create Vm

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { CreateVMOperationRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // CreateVMRequest
    createVMRequest: ...,
  } satisfies CreateVMOperationRequest;

  try {
    const data = await api.createVM(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **createVMRequest** | [CreateVMRequest](CreateVMRequest.md) |  | |

### Return type

[**CreateVMResponse**](CreateVMResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getOperationEvents

> GetOperationEvents200Response getOperationEvents(correlationId)

Get Operation Events

Stream operation results via Server-Sent Events (SSE) for public usage.  Returns a stream of events with the following format: - event: Event type (e.g., \&quot;connected\&quot;, \&quot;progress\&quot;, \&quot;complete\&quot;, \&quot;error\&quot;) - data: JSON payload with event details  Events: - connected: Initial connection established - progress: Operation progress update - complete: Operation completed successfully - error: Operation failed with error details 

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { GetOperationEventsRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // string
    correlationId: correlationId_example,
  } satisfies GetOperationEventsRequest;

  try {
    const data = await api.getOperationEvents(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **correlationId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**GetOperationEvents200Response**](GetOperationEvents200Response.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `text/event-stream`, `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Server-Sent Events stream |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## saveVmSnapshotApiPublicBuildVmPublicIdSnapshotPost

> CreateSnapshotResponse saveVmSnapshotApiPublicBuildVmPublicIdSnapshotPost(publicId, createSnapshotRequest)

Save Vm Snapshot

Save a snapshot of a VM.  Optional parameters allow overriding artifact labels: - service: Simulator name (defaults to job\&#39;s service) - git_hash: Git hash/version (defaults to job\&#39;s version or \&quot;unknown\&quot;) - dataset: Dataset name (defaults to job\&#39;s dataset) 

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { SaveVmSnapshotApiPublicBuildVmPublicIdSnapshotPostRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // string
    publicId: publicId_example,
    // CreateSnapshotRequest (optional)
    createSnapshotRequest: ...,
  } satisfies SaveVmSnapshotApiPublicBuildVmPublicIdSnapshotPostRequest;

  try {
    const data = await api.saveVmSnapshotApiPublicBuildVmPublicIdSnapshotPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **publicId** | `string` |  | [Defaults to `undefined`] |
| **createSnapshotRequest** | [CreateSnapshotRequest](CreateSnapshotRequest.md) |  | [Optional] |

### Return type

[**CreateSnapshotResponse**](CreateSnapshotResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## setupRootAccessApiPublicBuildVmPublicIdSetupRootAccessPost

> VMManagementResponse setupRootAccessApiPublicBuildVmPublicIdSetupRootAccessPost(publicId, setupRootPasswordRequest)

Setup Root Access

Setup SSH key-based authentication for the root user.

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { SetupRootAccessApiPublicBuildVmPublicIdSetupRootAccessPostRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // string
    publicId: publicId_example,
    // SetupRootPasswordRequest
    setupRootPasswordRequest: ...,
  } satisfies SetupRootAccessApiPublicBuildVmPublicIdSetupRootAccessPostRequest;

  try {
    const data = await api.setupRootAccessApiPublicBuildVmPublicIdSetupRootAccessPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **publicId** | `string` |  | [Defaults to `undefined`] |
| **setupRootPasswordRequest** | [SetupRootPasswordRequest](SetupRootPasswordRequest.md) |  | |

### Return type

[**VMManagementResponse**](VMManagementResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## setupSandbox

> SetupSandboxResponse setupSandbox(publicId, setupSandboxRequest)

Setup Sandbox

Setup sandbox development environment with git clone.

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { SetupSandboxOperationRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // string
    publicId: publicId_example,
    // SetupSandboxRequest
    setupSandboxRequest: ...,
  } satisfies SetupSandboxOperationRequest;

  try {
    const data = await api.setupSandbox(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **publicId** | `string` |  | [Defaults to `undefined`] |
| **setupSandboxRequest** | [SetupSandboxRequest](SetupSandboxRequest.md) |  | |

### Return type

[**SetupSandboxResponse**](SetupSandboxResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## startWorker

> VMManagementResponse startWorker(publicId, vMManagementRequest)

Start Worker

Start listeners: write env.py and worker compose from dataset config, then restart worker.

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { StartWorkerRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new PublicBuildApi(config);

  const body = {
    // string
    publicId: publicId_example,
    // VMManagementRequest
    vMManagementRequest: ...,
  } satisfies StartWorkerRequest;

  try {
    const data = await api.startWorker(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **publicId** | `string` |  | [Defaults to `undefined`] |
| **vMManagementRequest** | [VMManagementRequest](VMManagementRequest.md) |  | |

### Return type

[**VMManagementResponse**](VMManagementResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

