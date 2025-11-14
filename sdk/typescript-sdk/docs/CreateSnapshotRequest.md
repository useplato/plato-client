
# CreateSnapshotRequest

Request to create a VM snapshot with optional labeling.

## Properties

Name | Type
------------ | -------------
`service` | string
`gitHash` | string
`dataset` | string
`notes` | string
`flows` | string
`platoConfig` | string
`internalAppPort` | number
`messagingPort` | number

## Example

```typescript
import type { CreateSnapshotRequest } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "service": null,
  "gitHash": null,
  "dataset": null,
  "notes": null,
  "flows": null,
  "platoConfig": null,
  "internalAppPort": null,
  "messagingPort": null,
} satisfies CreateSnapshotRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CreateSnapshotRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


