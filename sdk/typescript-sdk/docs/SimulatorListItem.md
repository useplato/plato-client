
# SimulatorListItem


## Properties

Name | Type
------------ | -------------
`id` | number
`name` | string
`description` | string
`imgUrl` | string
`enabled` | boolean
`simType` | string
`jobName` | string
`internalAppPort` | number
`versionTag` | string
`imageUri` | string

## Example

```typescript
import type { SimulatorListItem } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "name": null,
  "description": null,
  "imgUrl": null,
  "enabled": null,
  "simType": null,
  "jobName": null,
  "internalAppPort": null,
  "versionTag": null,
  "imageUri": null,
} satisfies SimulatorListItem

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimulatorListItem
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


