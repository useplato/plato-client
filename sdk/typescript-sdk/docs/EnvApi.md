# EnvApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**backupEnvApiEnvJobGroupIdBackupPost**](EnvApi.md#backupenvapienvjobgroupidbackuppost) | **POST** /env/{job_group_id}/backup | Backup Env |
| [**closeEnvApiEnvJobGroupIdClosePost**](EnvApi.md#closeenvapienvjobgroupidclosepost) | **POST** /env/{job_group_id}/close | Close Env |
| [**createSimulatorApiEnvSimulatorsPost**](EnvApi.md#createsimulatorapienvsimulatorspost) | **POST** /env/simulators | Create Simulator |
| [**evaluateSessionApiEnvSessionSessionIdEvaluatePost**](EnvApi.md#evaluatesessionapienvsessionsessionidevaluatepost) | **POST** /env/session/{session_id}/evaluate | Evaluate Session |
| [**getActiveSessionApiEnvJobGroupIdActiveSessionGet**](EnvApi.md#getactivesessionapienvjobgroupidactivesessionget) | **GET** /env/{job_group_id}/active_session | Get Active Session |
| [**getCdpUrlApiEnvJobGroupIdCdpUrlGet**](EnvApi.md#getcdpurlapienvjobgroupidcdpurlget) | **GET** /env/{job_group_id}/cdp_url | Get Cdp Url |
| [**getEnvStateApiEnvJobGroupIdStateGet**](EnvApi.md#getenvstateapienvjobgroupidstateget) | **GET** /env/{job_group_id}/state | Get Env State |
| [**getJobStatusApiEnvJobGroupIdStatusGet**](EnvApi.md#getjobstatusapienvjobgroupidstatusget) | **GET** /env/{job_group_id}/status | Get Job Status |
| [**getProxyUrlApiEnvJobGroupIdProxyUrlGet**](EnvApi.md#getproxyurlapienvjobgroupidproxyurlget) | **GET** /env/{job_group_id}/proxy_url | Get Proxy Url |
| [**getSimulatorsApiEnvSimulatorsGet**](EnvApi.md#getsimulatorsapienvsimulatorsget) | **GET** /env/simulators | Get Simulators |
| [**getWorkerReadyApiEnvJobIdWorkerReadyGet**](EnvApi.md#getworkerreadyapienvjobidworkerreadyget) | **GET** /env/{job_id}/worker_ready | Get Worker Ready |
| [**logStateMutationApiEnvSessionIdLogPost**](EnvApi.md#logstatemutationapienvsessionidlogpost) | **POST** /env/{session_id}/log | Log State Mutation |
| [**makeEnvApiEnvMake2Post**](EnvApi.md#makeenvapienvmake2post) | **POST** /env/make2 | Make Env |
| [**resetEnvApiEnvJobGroupIdResetPost**](EnvApi.md#resetenvapienvjobgroupidresetpost) | **POST** /env/{job_group_id}/reset | Reset Env |
| [**scoreEnvApiEnvSessionSessionIdScorePost**](EnvApi.md#scoreenvapienvsessionsessionidscorepost) | **POST** /env/session/{session_id}/score | Score Env |
| [**sendHeartbeatApiEnvJobIdHeartbeatPost**](EnvApi.md#sendheartbeatapienvjobidheartbeatpost) | **POST** /env/{job_id}/heartbeat | Send Heartbeat |



## backupEnvApiEnvJobGroupIdBackupPost

> { [key: string]: any; } backupEnvApiEnvJobGroupIdBackupPost(jobGroupId, authorization, xInternalService)

Backup Env

Create a backup of the environment.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { BackupEnvApiEnvJobGroupIdBackupPostRequest } from '@plato-ai/sdk';

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
  } satisfies BackupEnvApiEnvJobGroupIdBackupPostRequest;

  try {
    const data = await api.backupEnvApiEnvJobGroupIdBackupPost(body);
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


## closeEnvApiEnvJobGroupIdClosePost

> { [key: string]: any; } closeEnvApiEnvJobGroupIdClosePost(jobGroupId, authorization, xInternalService)

Close Env

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { CloseEnvApiEnvJobGroupIdClosePostRequest } from '@plato-ai/sdk';

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
  } satisfies CloseEnvApiEnvJobGroupIdClosePostRequest;

  try {
    const data = await api.closeEnvApiEnvJobGroupIdClosePost(body);
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


## createSimulatorApiEnvSimulatorsPost

> { [key: string]: any; } createSimulatorApiEnvSimulatorsPost(createSimulatorRequest, authorization, xInternalService)

Create Simulator

Create a new simulator.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { CreateSimulatorApiEnvSimulatorsPostRequest } from '@plato-ai/sdk';

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
  } satisfies CreateSimulatorApiEnvSimulatorsPostRequest;

  try {
    const data = await api.createSimulatorApiEnvSimulatorsPost(body);
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


## evaluateSessionApiEnvSessionSessionIdEvaluatePost

> { [key: string]: any; } evaluateSessionApiEnvSessionSessionIdEvaluatePost(sessionId, authorization, xInternalService, evaluateRequest)

Evaluate Session

Evaluate the session.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { EvaluateSessionApiEnvSessionSessionIdEvaluatePostRequest } from '@plato-ai/sdk';

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
  } satisfies EvaluateSessionApiEnvSessionSessionIdEvaluatePostRequest;

  try {
    const data = await api.evaluateSessionApiEnvSessionSessionIdEvaluatePost(body);
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


## getActiveSessionApiEnvJobGroupIdActiveSessionGet

> { [key: string]: any; } getActiveSessionApiEnvJobGroupIdActiveSessionGet(jobGroupId, authorization, xInternalService)

Get Active Session

Get the active session for a job group.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetActiveSessionApiEnvJobGroupIdActiveSessionGetRequest } from '@plato-ai/sdk';

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
  } satisfies GetActiveSessionApiEnvJobGroupIdActiveSessionGetRequest;

  try {
    const data = await api.getActiveSessionApiEnvJobGroupIdActiveSessionGet(body);
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


## getCdpUrlApiEnvJobGroupIdCdpUrlGet

> { [key: string]: any; } getCdpUrlApiEnvJobGroupIdCdpUrlGet(jobGroupId, authorization, xInternalService)

Get Cdp Url

Get the CDP URL for the environment.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetCdpUrlApiEnvJobGroupIdCdpUrlGetRequest } from '@plato-ai/sdk';

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
  } satisfies GetCdpUrlApiEnvJobGroupIdCdpUrlGetRequest;

  try {
    const data = await api.getCdpUrlApiEnvJobGroupIdCdpUrlGet(body);
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


## getEnvStateApiEnvJobGroupIdStateGet

> { [key: string]: any; } getEnvStateApiEnvJobGroupIdStateGet(jobGroupId, authorization, xInternalService)

Get Env State

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetEnvStateApiEnvJobGroupIdStateGetRequest } from '@plato-ai/sdk';

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
  } satisfies GetEnvStateApiEnvJobGroupIdStateGetRequest;

  try {
    const data = await api.getEnvStateApiEnvJobGroupIdStateGet(body);
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


## getJobStatusApiEnvJobGroupIdStatusGet

> JobStatusResponse getJobStatusApiEnvJobGroupIdStatusGet(jobGroupId, authorization, xInternalService)

Get Job Status

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetJobStatusApiEnvJobGroupIdStatusGetRequest } from '@plato-ai/sdk';

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
  } satisfies GetJobStatusApiEnvJobGroupIdStatusGetRequest;

  try {
    const data = await api.getJobStatusApiEnvJobGroupIdStatusGet(body);
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


## getProxyUrlApiEnvJobGroupIdProxyUrlGet

> { [key: string]: any; } getProxyUrlApiEnvJobGroupIdProxyUrlGet(jobGroupId, authorization, xInternalService)

Get Proxy Url

Get the public URL for the environment.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetProxyUrlApiEnvJobGroupIdProxyUrlGetRequest } from '@plato-ai/sdk';

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
  } satisfies GetProxyUrlApiEnvJobGroupIdProxyUrlGetRequest;

  try {
    const data = await api.getProxyUrlApiEnvJobGroupIdProxyUrlGet(body);
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


## getSimulatorsApiEnvSimulatorsGet

> Array&lt;{ [key: string]: any; }&gt; getSimulatorsApiEnvSimulatorsGet(authorization, xInternalService)

Get Simulators

Get all simulators with optimized queries.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { GetSimulatorsApiEnvSimulatorsGetRequest } from '@plato-ai/sdk';

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
  } satisfies GetSimulatorsApiEnvSimulatorsGetRequest;

  try {
    const data = await api.getSimulatorsApiEnvSimulatorsGet(body);
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


## makeEnvApiEnvMake2Post

> MakeEnvResponse makeEnvApiEnvMake2Post(makeEnvRequest2, authorization, xInternalService)

Make Env

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { MakeEnvApiEnvMake2PostRequest } from '@plato-ai/sdk';

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
  } satisfies MakeEnvApiEnvMake2PostRequest;

  try {
    const data = await api.makeEnvApiEnvMake2Post(body);
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

[**MakeEnvResponse**](MakeEnvResponse.md)

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


## resetEnvApiEnvJobGroupIdResetPost

> { [key: string]: any; } resetEnvApiEnvJobGroupIdResetPost(jobGroupId, resetEnvRequest, authorization, xInternalService)

Reset Env

Reset the environment with an optional task.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { ResetEnvApiEnvJobGroupIdResetPostRequest } from '@plato-ai/sdk';

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
  } satisfies ResetEnvApiEnvJobGroupIdResetPostRequest;

  try {
    const data = await api.resetEnvApiEnvJobGroupIdResetPost(body);
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


## sendHeartbeatApiEnvJobIdHeartbeatPost

> { [key: string]: any; } sendHeartbeatApiEnvJobIdHeartbeatPost(jobId, authorization, xInternalService)

Send Heartbeat

Send a heartbeat to keep the environment session alive.

### Example

```ts
import {
  Configuration,
  EnvApi,
} from '@plato-ai/sdk';
import type { SendHeartbeatApiEnvJobIdHeartbeatPostRequest } from '@plato-ai/sdk';

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
  } satisfies SendHeartbeatApiEnvJobIdHeartbeatPostRequest;

  try {
    const data = await api.sendHeartbeatApiEnvJobIdHeartbeatPost(body);
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

