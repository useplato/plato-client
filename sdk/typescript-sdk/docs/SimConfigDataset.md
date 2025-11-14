
# SimConfigDataset

Configuration for a simulator dataset.

## Properties

Name | Type
------------ | -------------
`compute` | [SimConfigCompute](SimConfigCompute.md)
`metadata` | [SimConfigMetadata](SimConfigMetadata.md)
`services` | [{ [key: string]: SimConfigService; }](SimConfigService.md)
`listeners` | [{ [key: string]: SimConfigListener; }](SimConfigListener.md)

## Example

```typescript
import type { SimConfigDataset } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "compute": null,
  "metadata": null,
  "services": null,
  "listeners": null,
} satisfies SimConfigDataset

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimConfigDataset
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


