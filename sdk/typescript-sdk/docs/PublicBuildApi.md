# PublicBuildApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**checkpointVmApiPublicBuildVmPublicIdCheckpointPost**](PublicBuildApi.md#checkpointvmapipublicbuildvmpublicidcheckpointpost) | **POST** /public-build/vm/{public_id}/checkpoint | Checkpoint Vm |
| [**closeVmApiPublicBuildVmPublicIdDelete**](PublicBuildApi.md#closevmapipublicbuildvmpubliciddelete) | **DELETE** /public-build/vm/{public_id} | Close Vm |
| [**createVmApiPublicBuildVmCreatePost**](PublicBuildApi.md#createvmapipublicbuildvmcreatepost) | **POST** /public-build/vm/create | Create Vm |
| [**getOperationEventsApiPublicBuildEventsCorrelationIdGet**](PublicBuildApi.md#getoperationeventsapipublicbuildeventscorrelationidget) | **GET** /public-build/events/{correlation_id} | Get Operation Events |
| [**saveVmSnapshotApiPublicBuildVmPublicIdSnapshotPost**](PublicBuildApi.md#savevmsnapshotapipublicbuildvmpublicidsnapshotpost) | **POST** /public-build/vm/{public_id}/snapshot | Save Vm Snapshot |
| [**setupRootAccessApiPublicBuildVmPublicIdSetupRootAccessPost**](PublicBuildApi.md#setuprootaccessapipublicbuildvmpublicidsetuprootaccesspost) | **POST** /public-build/vm/{public_id}/setup-root-access | Setup Root Access |
| [**setupSandboxApiPublicBuildVmPublicIdSetupSandboxPost**](PublicBuildApi.md#setupsandboxapipublicbuildvmpublicidsetupsandboxpost) | **POST** /public-build/vm/{public_id}/setup-sandbox | Setup Sandbox |
| [**startWorkerApiPublicBuildVmPublicIdStartWorkerPost**](PublicBuildApi.md#startworkerapipublicbuildvmpublicidstartworkerpost) | **POST** /public-build/vm/{public_id}/start-worker | Start Worker |



## checkpointVmApiPublicBuildVmPublicIdCheckpointPost

> CreateSnapshotResponse checkpointVmApiPublicBuildVmPublicIdCheckpointPost(publicId, createSnapshotRequest)

Checkpoint Vm

Create a checkpoint snapshot of a VM.  This creates a blockdiff_checkpoint artifact type instead of a regular blockdiff. Optional parameters allow overriding artifact labels: - service: Simulator name (defaults to job\&#39;s service) - git_hash: Git hash/version (defaults to job\&#39;s version or \&quot;unknown\&quot;) - dataset: Dataset name (defaults to job\&#39;s dataset) 

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { CheckpointVmApiPublicBuildVmPublicIdCheckpointPostRequest } from '@plato-ai/sdk';

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
  } satisfies CheckpointVmApiPublicBuildVmPublicIdCheckpointPostRequest;

  try {
    const data = await api.checkpointVmApiPublicBuildVmPublicIdCheckpointPost(body);
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


## closeVmApiPublicBuildVmPublicIdDelete

> VMManagementResponse closeVmApiPublicBuildVmPublicIdDelete(publicId)

Close Vm

Close and terminate a VM.

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { CloseVmApiPublicBuildVmPublicIdDeleteRequest } from '@plato-ai/sdk';

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
  } satisfies CloseVmApiPublicBuildVmPublicIdDeleteRequest;

  try {
    const data = await api.closeVmApiPublicBuildVmPublicIdDelete(body);
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


## createVmApiPublicBuildVmCreatePost

> CreateVMResponse createVmApiPublicBuildVmCreatePost(createVMRequest)

Create Vm

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { CreateVmApiPublicBuildVmCreatePostRequest } from '@plato-ai/sdk';

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
  } satisfies CreateVmApiPublicBuildVmCreatePostRequest;

  try {
    const data = await api.createVmApiPublicBuildVmCreatePost(body);
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


## getOperationEventsApiPublicBuildEventsCorrelationIdGet

> GetOperationEventsApiPublicBuildEventsCorrelationIdGet200Response getOperationEventsApiPublicBuildEventsCorrelationIdGet(correlationId)

Get Operation Events

Stream operation results via Server-Sent Events (SSE) for public usage.  Returns a stream of events with the following format: - event: Event type (e.g., \&quot;connected\&quot;, \&quot;progress\&quot;, \&quot;complete\&quot;, \&quot;error\&quot;) - data: JSON payload with event details  Events: - connected: Initial connection established - progress: Operation progress update - complete: Operation completed successfully - error: Operation failed with error details 

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { GetOperationEventsApiPublicBuildEventsCorrelationIdGetRequest } from '@plato-ai/sdk';

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
  } satisfies GetOperationEventsApiPublicBuildEventsCorrelationIdGetRequest;

  try {
    const data = await api.getOperationEventsApiPublicBuildEventsCorrelationIdGet(body);
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

[**GetOperationEventsApiPublicBuildEventsCorrelationIdGet200Response**](GetOperationEventsApiPublicBuildEventsCorrelationIdGet200Response.md)

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


## setupSandboxApiPublicBuildVmPublicIdSetupSandboxPost

> SetupSandboxResponse setupSandboxApiPublicBuildVmPublicIdSetupSandboxPost(publicId, setupSandboxRequest)

Setup Sandbox

Setup sandbox development environment with git clone.

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { SetupSandboxApiPublicBuildVmPublicIdSetupSandboxPostRequest } from '@plato-ai/sdk';

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
  } satisfies SetupSandboxApiPublicBuildVmPublicIdSetupSandboxPostRequest;

  try {
    const data = await api.setupSandboxApiPublicBuildVmPublicIdSetupSandboxPost(body);
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


## startWorkerApiPublicBuildVmPublicIdStartWorkerPost

> VMManagementResponse startWorkerApiPublicBuildVmPublicIdStartWorkerPost(publicId, vMManagementRequest)

Start Worker

Start listeners: write env.py and worker compose from dataset config, then restart worker.

### Example

```ts
import {
  Configuration,
  PublicBuildApi,
} from '@plato-ai/sdk';
import type { StartWorkerApiPublicBuildVmPublicIdStartWorkerPostRequest } from '@plato-ai/sdk';

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
  } satisfies StartWorkerApiPublicBuildVmPublicIdStartWorkerPostRequest;

  try {
    const data = await api.startWorkerApiPublicBuildVmPublicIdStartWorkerPost(body);
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

