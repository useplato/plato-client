
# SimStatusHistory


## Properties

Name | Type
------------ | -------------
`timestampIso` | string
`oldStatus` | string
`newStatus` | string
`userId` | number

## Example

```typescript
import type { SimStatusHistory } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "timestampIso": null,
  "oldStatus": null,
  "newStatus": null,
  "userId": null,
} satisfies SimStatusHistory

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimStatusHistory
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


