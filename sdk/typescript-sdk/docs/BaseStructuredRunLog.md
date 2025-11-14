
# BaseStructuredRunLog


## Properties

Name | Type
------------ | -------------
`source` | string
`type` | string
`timestamp` | string

## Example

```typescript
import type { BaseStructuredRunLog } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "source": null,
  "type": null,
  "timestamp": null,
} satisfies BaseStructuredRunLog

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BaseStructuredRunLog
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


