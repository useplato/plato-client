# TestcasesApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getTestcasesApiTestcasesGet**](TestcasesApi.md#gettestcasesapitestcasesget) | **GET** /testcases | Get Testcases |



## getTestcasesApiTestcasesGet

> any getTestcasesApiTestcasesGet(startPath, testCaseSetIds, name, prompt, mode, page, pageSize, simulatorId, simulatorName, testCasePublicId, scoringConfigType, isAssigned, isSample, rejected, excludeAssignedToAnnotators)

Get Testcases

### Example

```ts
import {
  Configuration,
  TestcasesApi,
} from '@plato-ai/sdk';
import type { GetTestcasesApiTestcasesGetRequest } from '@plato-ai/sdk';

async function example() {
  console.log("🚀 Testing @plato-ai/sdk SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: ApiKeyAuth
    apiKey: "YOUR API KEY",
  });
  const api = new TestcasesApi(config);

  const body = {
    // string (optional)
    startPath: startPath_example,
    // string (optional)
    testCaseSetIds: testCaseSetIds_example,
    // string (optional)
    name: name_example,
    // string (optional)
    prompt: prompt_example,
    // string (optional)
    mode: mode_example,
    // number (optional)
    page: 56,
    // number (optional)
    pageSize: 56,
    // number (optional)
    simulatorId: 56,
    // string (optional)
    simulatorName: simulatorName_example,
    // string (optional)
    testCasePublicId: testCasePublicId_example,
    // string (optional)
    scoringConfigType: scoringConfigType_example,
    // boolean (optional)
    isAssigned: true,
    // boolean (optional)
    isSample: true,
    // boolean (optional)
    rejected: true,
    // boolean (optional)
    excludeAssignedToAnnotators: true,
  } satisfies GetTestcasesApiTestcasesGetRequest;

  try {
    const data = await api.getTestcasesApiTestcasesGet(body);
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
| **startPath** | `string` |  | [Optional] [Defaults to `undefined`] |
| **testCaseSetIds** | `string` |  | [Optional] [Defaults to `undefined`] |
| **name** | `string` |  | [Optional] [Defaults to `undefined`] |
| **prompt** | `string` |  | [Optional] [Defaults to `undefined`] |
| **mode** | `string` |  | [Optional] [Defaults to `undefined`] |
| **page** | `number` |  | [Optional] [Defaults to `undefined`] |
| **pageSize** | `number` |  | [Optional] [Defaults to `30`] |
| **simulatorId** | `number` |  | [Optional] [Defaults to `undefined`] |
| **simulatorName** | `string` |  | [Optional] [Defaults to `undefined`] |
| **testCasePublicId** | `string` |  | [Optional] [Defaults to `undefined`] |
| **scoringConfigType** | `string` |  | [Optional] [Defaults to `undefined`] |
| **isAssigned** | `boolean` |  | [Optional] [Defaults to `undefined`] |
| **isSample** | `boolean` |  | [Optional] [Defaults to `undefined`] |
| **rejected** | `boolean` |  | [Optional] [Defaults to `undefined`] |
| **excludeAssignedToAnnotators** | `boolean` |  | [Optional] [Defaults to `undefined`] |

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

