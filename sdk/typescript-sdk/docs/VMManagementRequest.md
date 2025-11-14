
# VMManagementRequest


## Properties

Name | Type
------------ | -------------
`service` | string
`dataset` | string
`platoDatasetConfig` | [SimConfigDataset](SimConfigDataset.md)
`requestTimeout` | number

## Example

```typescript
import type { VMManagementRequest } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "service": null,
  "dataset": null,
  "platoDatasetConfig": null,
  "requestTimeout": null,
} satisfies VMManagementRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as VMManagementRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


