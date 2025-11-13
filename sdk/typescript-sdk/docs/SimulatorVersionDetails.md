
# SimulatorVersionDetails


## Properties

Name | Type
------------ | -------------
`artifactId` | string
`version` | string
`createdAt` | Date
`workerImage` | string
`ecsTaskDefinitionArn` | string
`snapshotS3Uri` | string
`dataset` | string

## Example

```typescript
import type { SimulatorVersionDetails } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "artifactId": null,
  "version": null,
  "createdAt": null,
  "workerImage": null,
  "ecsTaskDefinitionArn": null,
  "snapshotS3Uri": null,
  "dataset": null,
} satisfies SimulatorVersionDetails

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimulatorVersionDetails
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


