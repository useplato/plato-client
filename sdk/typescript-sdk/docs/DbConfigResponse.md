
# DbConfigResponse

Database configuration from plato config

## Properties

Name | Type
------------ | -------------
`dbType` | string
`dbPort` | number
`dbUser` | string
`dbPassword` | string
`dbDatabase` | string

## Example

```typescript
import type { DbConfigResponse } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "dbType": null,
  "dbPort": null,
  "dbUser": null,
  "dbPassword": null,
  "dbDatabase": null,
} satisfies DbConfigResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DbConfigResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


