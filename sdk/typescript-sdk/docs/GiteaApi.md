# GiteaApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createSimulatorRepository**](GiteaApi.md#createsimulatorrepository) | **POST** /gitea/simulators/{simulator_id}/repo | Create Simulator Repository |
| [**getAccessibleSimulators**](GiteaApi.md#getaccessiblesimulators) | **GET** /gitea/simulators | Get Accessible Simulators |
| [**getGiteaCredentials**](GiteaApi.md#getgiteacredentials) | **GET** /gitea/credentials | Get Gitea Credentials |
| [**getMyGiteaInfo**](GiteaApi.md#getmygiteainfo) | **GET** /gitea/my-info | Get My Gitea Info |
| [**getSimulatorRepository**](GiteaApi.md#getsimulatorrepository) | **GET** /gitea/simulators/{simulator_id}/repo | Get Simulator Repository |



## createSimulatorRepository

> { [key: string]: any; } createSimulatorRepository(simulatorId, authorization, xInternalService)

Create Simulator Repository

Create a repository for a simulator (only if it doesn\&#39;t exist)

### Example

```ts
import {
  Configuration,
  GiteaApi,
} from '@plato-ai/sdk';
import type { CreateSimulatorRepositoryRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new GiteaApi(config);

  const body = {
    // number
    simulatorId: 56,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies CreateSimulatorRepositoryRequest;

  try {
    const data = await api.createSimulatorRepository(body);
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
| **simulatorId** | `number` |  | [Defaults to `undefined`] |
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


## getAccessibleSimulators

> Array&lt;{ [key: string]: any; }&gt; getAccessibleSimulators(authorization, xInternalService)

Get Accessible Simulators

Get simulators that user has access to view repos for

### Example

```ts
import {
  Configuration,
  GiteaApi,
} from '@plato-ai/sdk';
import type { GetAccessibleSimulatorsRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new GiteaApi(config);

  const body = {
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetAccessibleSimulatorsRequest;

  try {
    const data = await api.getAccessibleSimulators(body);
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


## getGiteaCredentials

> { [key: string]: any; } getGiteaCredentials(authorization, xInternalService)

Get Gitea Credentials

Get Gitea credentials for the organization

### Example

```ts
import {
  Configuration,
  GiteaApi,
} from '@plato-ai/sdk';
import type { GetGiteaCredentialsRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new GiteaApi(config);

  const body = {
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetGiteaCredentialsRequest;

  try {
    const data = await api.getGiteaCredentials(body);
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


## getMyGiteaInfo

> { [key: string]: any; } getMyGiteaInfo(authorization, xInternalService)

Get My Gitea Info

Get the current user\&#39;s Gitea info (auto-provisions if needed)

### Example

```ts
import {
  Configuration,
  GiteaApi,
} from '@plato-ai/sdk';
import type { GetMyGiteaInfoRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new GiteaApi(config);

  const body = {
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetMyGiteaInfoRequest;

  try {
    const data = await api.getMyGiteaInfo(body);
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


## getSimulatorRepository

> { [key: string]: any; } getSimulatorRepository(simulatorId, authorization, xInternalService)

Get Simulator Repository

Get repository details for a specific simulator

### Example

```ts
import {
  Configuration,
  GiteaApi,
} from '@plato-ai/sdk';
import type { GetSimulatorRepositoryRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new GiteaApi(config);

  const body = {
    // number
    simulatorId: 56,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetSimulatorRepositoryRequest;

  try {
    const data = await api.getSimulatorRepository(body);
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
| **simulatorId** | `number` |  | [Defaults to `undefined`] |
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

