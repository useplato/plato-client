# EnvApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**backupEnvironment**](EnvApi.md#backupenvironment) | **POST** /env/{job_group_id}/backup | Backup Env |
| [**closeEnvironment**](EnvApi.md#closeenvironment) | **POST** /env/{job_group_id}/close | Close Env |
| [**createSimulator**](EnvApi.md#createsimulatoroperation) | **POST** /env/simulators | Create Simulator |
| [**evaluateSession**](EnvApi.md#evaluatesession) | **POST** /env/session/{session_id}/evaluate | Evaluate Session |
| [**getActiveSession**](EnvApi.md#getactivesession) | **GET** /env/{job_group_id}/active_session | Get Active Session |
| [**getCdpUrl**](EnvApi.md#getcdpurl) | **GET** /env/{job_group_id}/cdp_url | Get Cdp Url |
| [**getEnvironmentState**](EnvApi.md#getenvironmentstate) | **GET** /env/{job_group_id}/state | Get Env State |
| [**getJobStatus**](EnvApi.md#getjobstatus) | **GET** /env/{job_group_id}/status | Get Job Status |
| [**getProxyUrl**](EnvApi.md#getproxyurl) | **GET** /env/{job_group_id}/proxy_url | Get Proxy Url |
| [**getSimulators**](EnvApi.md#getsimulators) | **GET** /env/simulators | Get Simulators |
| [**getWorkerReadyApiEnvJobIdWorkerReadyGet**](EnvApi.md#getworkerreadyapienvjobidworkerreadyget) | **GET** /env/{job_id}/worker_ready | Get Worker Ready |
| [**logStateMutationApiEnvSessionIdLogPost**](EnvApi.md#logstatemutationapienvsessionidlogpost) | **POST** /env/{session_id}/log | Log State Mutation |
| [**makeEnvironment**](EnvApi.md#makeenvironment) | **POST** /env/make2 | Make Env |
| [**resetEnvironment**](EnvApi.md#resetenvironment) | **POST** /env/{job_group_id}/reset | Reset Env |
| [**scoreEnvApiEnvSessionSessionIdScorePost**](EnvApi.md#scoreenvapienvsessionsessionidscorepost) | **POST** /env/session/{session_id}/score | Score Env |
| [**sendHeartbeat**](EnvApi.md#sendheartbeat) | **POST** /env/{job_id}/heartbeat | Send Heartbeat |



## backupEnvironment

> { [key: string]: any; } backupEnvironment(jobGroupId, authorization, xInternalService)

Backup Env

Create a backup of the environment.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { BackupEnvironmentRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies BackupEnvironmentRequest;

  try {
    const data = await api.backupEnvironment(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## closeEnvironment

> { [key: string]: any; } closeEnvironment(jobGroupId, authorization, xInternalService)

Close Env

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { CloseEnvironmentRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies CloseEnvironmentRequest;

  try {
    const data = await api.closeEnvironment(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## createSimulator

> { [key: string]: any; } createSimulator(createSimulatorRequest, authorization, xInternalService)

Create Simulator

Create a new simulator.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { CreateSimulatorOperationRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // CreateSimulatorRequest
    createSimulatorRequest: ...,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies CreateSimulatorOperationRequest;

  try {
    const data = await api.createSimulator(body);
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
| **createSimulatorRequest** | [CreateSimulatorRequest](CreateSimulatorRequest.md) |  | |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## evaluateSession

> { [key: string]: any; } evaluateSession(sessionId, authorization, xInternalService, evaluateRequest)

Evaluate Session

Evaluate the session.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { EvaluateSessionRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    sessionId: sessionId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
    // EvaluateRequest (optional)
    evaluateRequest: ...,
  } satisfies EvaluateSessionRequest;

  try {
    const data = await api.evaluateSession(body);
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
| **sessionId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |
| **evaluateRequest** | [EvaluateRequest](EvaluateRequest.md) |  | [Optional] |

### Return type

**{ [key: string]: any; }**

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


## getActiveSession

> { [key: string]: any; } getActiveSession(jobGroupId, authorization, xInternalService)

Get Active Session

Get the active session for a job group.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetActiveSessionRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetActiveSessionRequest;

  try {
    const data = await api.getActiveSession(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## getCdpUrl

> { [key: string]: any; } getCdpUrl(jobGroupId, authorization, xInternalService)

Get Cdp Url

Get the CDP URL for the environment.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetCdpUrlRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetCdpUrlRequest;

  try {
    const data = await api.getCdpUrl(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## getEnvironmentState

> { [key: string]: any; } getEnvironmentState(jobGroupId, authorization, xInternalService)

Get Env State

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetEnvironmentStateRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetEnvironmentStateRequest;

  try {
    const data = await api.getEnvironmentState(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## getJobStatus

> JobStatusResponse getJobStatus(jobGroupId, authorization, xInternalService)

Get Job Status

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetJobStatusRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetJobStatusRequest;

  try {
    const data = await api.getJobStatus(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**JobStatusResponse**](JobStatusResponse.md)

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


## getProxyUrl

> { [key: string]: any; } getProxyUrl(jobGroupId, authorization, xInternalService)

Get Proxy Url

Get the public URL for the environment.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetProxyUrlRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetProxyUrlRequest;

  try {
    const data = await api.getProxyUrl(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## getSimulators

> Array&lt;{ [key: string]: any; }&gt; getSimulators(authorization, xInternalService)

Get Simulators

Get all simulators with optimized queries.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetSimulatorsRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetSimulatorsRequest;

  try {
    const data = await api.getSimulators(body);
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
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**Array<{ [key: string]: any; }>**

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


## getWorkerReadyApiEnvJobIdWorkerReadyGet

> WorkerReadyResponse getWorkerReadyApiEnvJobIdWorkerReadyGet(jobId, timeout, authorization, xInternalService)

Get Worker Ready

Check if the workers for this job group are ready and healthy.  Uses the persistent job ready notification service to wait for job readiness. Falls back to checking Redis if notification not received (in case we missed it). Raises 500 if job not ready after all checks. 

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetWorkerReadyApiEnvJobIdWorkerReadyGetRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobId: jobId_example,
    // number (optional)
    timeout: 56,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetWorkerReadyApiEnvJobIdWorkerReadyGetRequest;

  try {
    const data = await api.getWorkerReadyApiEnvJobIdWorkerReadyGet(body);
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
| **jobId** | `string` |  | [Defaults to `undefined`] |
| **timeout** | `number` |  | [Optional] [Defaults to `120`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**WorkerReadyResponse**](WorkerReadyResponse.md)

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


## logStateMutationApiEnvSessionIdLogPost

> { [key: string]: any; } logStateMutationApiEnvSessionIdLogPost(sessionId, log)

Log State Mutation

Log a state mutation or batch of mutations.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { LogStateMutationApiEnvSessionIdLogPostRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    sessionId: sessionId_example,
    // Log
    log: ...,
  } satisfies LogStateMutationApiEnvSessionIdLogPostRequest;

  try {
    const data = await api.logStateMutationApiEnvSessionIdLogPost(body);
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
| **sessionId** | `string` |  | [Defaults to `undefined`] |
| **log** | [Log](Log.md) |  | |

### Return type

**{ [key: string]: any; }**

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


## makeEnvironment

> { [key: string]: any; } makeEnvironment(makeEnvRequest2, authorization, xInternalService)

Make Env

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { MakeEnvironmentRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // MakeEnvRequest2
    makeEnvRequest2: ...,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies MakeEnvironmentRequest;

  try {
    const data = await api.makeEnvironment(body);
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
| **makeEnvRequest2** | [MakeEnvRequest2](MakeEnvRequest2.md) |  | |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## resetEnvironment

> { [key: string]: any; } resetEnvironment(jobGroupId, resetEnvRequest, authorization, xInternalService)

Reset Env

Reset the environment with an optional task.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { ResetEnvironmentRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobGroupId: jobGroupId_example,
    // ResetEnvRequest
    resetEnvRequest: ...,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies ResetEnvironmentRequest;

  try {
    const data = await api.resetEnvironment(body);
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
| **jobGroupId** | `string` |  | [Defaults to `undefined`] |
| **resetEnvRequest** | [ResetEnvRequest](ResetEnvRequest.md) |  | |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## scoreEnvApiEnvSessionSessionIdScorePost

> { [key: string]: any; } scoreEnvApiEnvSessionSessionIdScorePost(sessionId, scoreRequest, authorization, xInternalService)

Score Env

Score the environment.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { ScoreEnvApiEnvSessionSessionIdScorePostRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    sessionId: sessionId_example,
    // ScoreRequest
    scoreRequest: ...,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies ScoreEnvApiEnvSessionSessionIdScorePostRequest;

  try {
    const data = await api.scoreEnvApiEnvSessionSessionIdScorePost(body);
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
| **sessionId** | `string` |  | [Defaults to `undefined`] |
| **scoreRequest** | [ScoreRequest](ScoreRequest.md) |  | |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## sendHeartbeat

> { [key: string]: any; } sendHeartbeat(jobId, authorization, xInternalService)

Send Heartbeat

Send a heartbeat to keep the environment session alive.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { SendHeartbeatRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new EnvApi(config);

  const body = {
    // string
    jobId: jobId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies SendHeartbeatRequest;

  try {
    const data = await api.sendHeartbeat(body);
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
| **jobId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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

