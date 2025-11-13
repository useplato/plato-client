
# SimulatorVersionsResponse


## Properties

Name | Type
------------ | -------------
`simulatorName` | string
`versions` | [Array&lt;SimulatorVersionDetails&gt;](SimulatorVersionDetails.md)
`totalVersions` | number

## Example

```typescript
import type { SimulatorVersionsResponse } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "simulatorName": null,
  "versions": null,
  "totalVersions": null,
} satisfies SimulatorVersionsResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimulatorVersionsResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


