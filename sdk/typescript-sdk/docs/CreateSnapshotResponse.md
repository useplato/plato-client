
# CreateSnapshotResponse

Response from creating a VM snapshot.

## Properties

Name | Type
------------ | -------------
`artifactId` | string
`status` | string
`timestamp` | string
`correlationId` | string
`s3Uri` | string

## Example

```typescript
import type { CreateSnapshotResponse } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "artifactId": null,
  "status": null,
  "timestamp": null,
  "correlationId": null,
  "s3Uri": null,
} satisfies CreateSnapshotResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CreateSnapshotResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


