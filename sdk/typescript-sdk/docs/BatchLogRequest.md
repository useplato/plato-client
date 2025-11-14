
# BatchLogRequest


## Properties

Name | Type
------------ | -------------
`source` | string
`type` | string
`timestamp` | string
`sessionId` | string
`mutations` | [Array&lt;BaseStructuredRunLog&gt;](BaseStructuredRunLog.md)
`count` | number

## Example

```typescript
import type { BatchLogRequest } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "source": null,
  "type": null,
  "timestamp": null,
  "sessionId": null,
  "mutations": null,
  "count": null,
} satisfies BatchLogRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BatchLogRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


