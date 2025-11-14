
# ResetEnvTask


## Properties

Name | Type
------------ | -------------
`prompt` | string
`startUrl` | string
`name` | string
`datasetName` | string
`evalConfig` | [BaseScoringConfig](BaseScoringConfig.md)

## Example

```typescript
import type { ResetEnvTask } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "prompt": null,
  "startUrl": null,
  "name": null,
  "datasetName": null,
  "evalConfig": null,
} satisfies ResetEnvTask

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ResetEnvTask
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


