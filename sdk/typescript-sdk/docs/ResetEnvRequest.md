
# ResetEnvRequest


## Properties

Name | Type
------------ | -------------
`task` | [ResetEnvTask](ResetEnvTask.md)
`agentVersion` | string
`model` | string
`source` | string
`loadBrowserState` | boolean
`viewportWidth` | number
`viewportHeight` | number
`testCasePublicId` | string
`replayedFromSessionId` | string
`userId` | number

## Example

```typescript
import type { ResetEnvRequest } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "task": null,
  "agentVersion": null,
  "model": null,
  "source": null,
  "loadBrowserState": null,
  "viewportWidth": null,
  "viewportHeight": null,
  "testCasePublicId": null,
  "replayedFromSessionId": null,
  "userId": null,
} satisfies ResetEnvRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ResetEnvRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


