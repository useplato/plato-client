
# SimConfigCompute

Compute resource configuration for a simulator.

## Properties

Name | Type
------------ | -------------
`cpus` | number
`memory` | number
`disk` | number
`appPort` | number
`platoMessagingPort` | number

## Example

```typescript
import type { SimConfigCompute } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "cpus": null,
  "memory": null,
  "disk": null,
  "appPort": null,
  "platoMessagingPort": null,
} satisfies SimConfigCompute

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimConfigCompute
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


