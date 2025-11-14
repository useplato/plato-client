
# CreateVMResponse


## Properties

Name | Type
------------ | -------------
`status` | string
`timestamp` | string
`correlationId` | string
`url` | string
`jobPublicId` | string
`jobGroupId` | string

## Example

```typescript
import type { CreateVMResponse } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "status": null,
  "timestamp": null,
  "correlationId": null,
  "url": null,
  "jobPublicId": null,
  "jobGroupId": null,
} satisfies CreateVMResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CreateVMResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


