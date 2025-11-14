
# WorkerReadyResponse

Response model for worker ready endpoint.

## Properties

Name | Type
------------ | -------------
`ready` | boolean
`jobId` | string
`workerPrivateIp` | string
`workerPublicIp` | string
`meshIp` | string
`workerPort` | number
`healthStatus` | { [key: string]: any; }
`error` | string

## Example

```typescript
import type { WorkerReadyResponse } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "ready": null,
  "jobId": null,
  "workerPrivateIp": null,
  "workerPublicIp": null,
  "meshIp": null,
  "workerPort": null,
  "healthStatus": null,
  "error": null,
} satisfies WorkerReadyResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as WorkerReadyResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


