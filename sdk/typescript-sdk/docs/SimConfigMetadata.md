
# SimConfigMetadata

Metadata configuration for a simulator.

## Properties

Name | Type
------------ | -------------
`favicon` | string
`name` | string
`description` | string
`sourceCodeUrl` | string
`startUrl` | string
`license` | string
`variables` | Array&lt;{ [key: string]: string; }&gt;
`flowsPath` | string

## Example

```typescript
import type { SimConfigMetadata } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "favicon": null,
  "name": null,
  "description": null,
  "sourceCodeUrl": null,
  "startUrl": null,
  "license": null,
  "variables": null,
  "flowsPath": null,
} satisfies SimConfigMetadata

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimConfigMetadata
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


