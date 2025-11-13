# UserApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getOrganizationRunningSessionsEndpointApiUserOrganizationRunningSessionsGet**](UserApi.md#getorganizationrunningsessionsendpointapiuserorganizationrunningsessionsget) | **GET** /user/organization/running-sessions | Get Organization Running Sessions Endpoint |



## getOrganizationRunningSessionsEndpointApiUserOrganizationRunningSessionsGet

> any getOrganizationRunningSessionsEndpointApiUserOrganizationRunningSessionsGet(lastNHours)

Get Organization Running Sessions Endpoint

Get comprehensive session information for the user\&#39;s organization.  Args:     last_n_hours: Number of hours to look back for peak calculation (default: 1)  Returns:     Dictionary containing:     - running_sessions: Count of currently running sessions     - pending_sessions: Count of sessions that are not ended but have status !&#x3D; RUN_STARTED     - peak_running_count: Peak number of running sessions within the past last_n_hours period 

### Example

```ts
import {
  Configuration,
  UserApi,
} from '@plato-ai/sdk';
import type { GetOrganizationRunningSessionsEndpointApiUserOrganizationRunningSessionsGetRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new UserApi(config);

  const body = {
    // number | Number of hours to look back for peak calculation (default: 1) (optional)
    lastNHours: 56,
  } satisfies GetOrganizationRunningSessionsEndpointApiUserOrganizationRunningSessionsGetRequest;

  try {
    const data = await api.getOrganizationRunningSessionsEndpointApiUserOrganizationRunningSessionsGet(body);
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
| **lastNHours** | `number` | Number of hours to look back for peak calculation (default: 1) | [Optional] [Defaults to `1`] |

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

