
# CreateSimulatorRequest


## Properties

Name | Type
------------ | -------------
`name` | string
`url` | string
`description` | string
`imgUrl` | string
`config` | [SimulatorConfig](SimulatorConfig.md)
`ancestors` | Array&lt;string&gt;
`enabled` | boolean
`simType` | string
`jobName` | string
`internalAppPort` | number
`supportedProviders` | Array&lt;string&gt;

## Example

```typescript
import type { CreateSimulatorRequest } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "url": null,
  "description": null,
  "imgUrl": null,
  "config": null,
  "ancestors": null,
  "enabled": null,
  "simType": null,
  "jobName": null,
  "internalAppPort": null,
  "supportedProviders": null,
} satisfies CreateSimulatorRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CreateSimulatorRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


