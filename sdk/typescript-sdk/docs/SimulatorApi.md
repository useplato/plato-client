# SimulatorApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getSimulatorDbConfig**](SimulatorApi.md#getsimulatordbconfig) | **GET** /simulator/{artifact_id}/db_config | Get Db Config |
| [**getSimulatorFlows**](SimulatorApi.md#getsimulatorflows) | **GET** /simulator/{artifact_id}/flows | Get Env Flows |
| [**getSimulatorVersions**](SimulatorApi.md#getsimulatorversions) | **GET** /simulator/{simulator_name}/versions | Get Simulator Versions |



## getSimulatorDbConfig

> DbConfigResponse getSimulatorDbConfig(artifactId, authorization, xInternalService)

Get Db Config

Get database configuration from a simulator artifact\&#39;s plato config.  Parses the YAML plato_config and extracts the database listener configuration. The plato_config contains a single dataset configuration (anchors are already resolved). 

### Example

```ts
import {
  Configuration,
  SimulatorApi,
} from '@plato-ai/sdk';
import type { GetSimulatorDbConfigRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new SimulatorApi(config);

  const body = {
    // string
    artifactId: artifactId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetSimulatorDbConfigRequest;

  try {
    const data = await api.getSimulatorDbConfig(body);
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
| **artifactId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**DbConfigResponse**](DbConfigResponse.md)

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


## getSimulatorFlows

> any getSimulatorFlows(artifactId, authorization, xInternalService)

Get Env Flows

### Example

```ts
import {
  Configuration,
  SimulatorApi,
} from '@plato-ai/sdk';
import type { GetSimulatorFlowsRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new SimulatorApi(config);

  const body = {
    // string
    artifactId: artifactId_example,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetSimulatorFlowsRequest;

  try {
    const data = await api.getSimulatorFlows(body);
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
| **artifactId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**any**

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


## getSimulatorVersions

> SimulatorVersionsResponse getSimulatorVersions(simulatorName, includeCheckpoints, authorization, xInternalService)

Get Simulator Versions

Get all versions for a specific simulator across all datasets

### Example

```ts
import {
  Configuration,
  SimulatorApi,
} from '@plato-ai/sdk';
import type { GetSimulatorVersionsRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new SimulatorApi(config);

  const body = {
    // string
    simulatorName: simulatorName_example,
    // boolean | Include blockdiff checkpoint artifacts (optional)
    includeCheckpoints: true,
    // string (optional)
    authorization: authorization_example,
    // string (optional)
    xInternalService: xInternalService_example,
  } satisfies GetSimulatorVersionsRequest;

  try {
    const data = await api.getSimulatorVersions(body);
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
| **simulatorName** | `string` |  | [Defaults to `undefined`] |
| **includeCheckpoints** | `boolean` | Include blockdiff checkpoint artifacts | [Optional] [Defaults to `false`] |
| **authorization** | `string` |  | [Optional] [Defaults to `undefined`] |
| **xInternalService** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**SimulatorVersionsResponse**](SimulatorVersionsResponse.md)

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

