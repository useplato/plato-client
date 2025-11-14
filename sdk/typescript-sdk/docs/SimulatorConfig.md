
# SimulatorConfig


## Properties

Name | Type
------------ | -------------
`type` | string
`cookies` | [Array&lt;ChromeCookie&gt;](ChromeCookie.md)
`authentication` | [Authentication](Authentication.md)
`defaultStartPath` | string
`status` | string
`envAssignees` | Array&lt;number&gt;
`envReviewAssignees` | Array&lt;number&gt;
`dataAssignees` | Array&lt;number&gt;
`dataReviewAssignees` | Array&lt;number&gt;
`statusHistory` | [Array&lt;SimStatusHistory&gt;](SimStatusHistory.md)
`assignedUserId` | number
`notes` | string

## Example

```typescript
import type { SimulatorConfig } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "type": null,
  "cookies": null,
  "authentication": null,
  "defaultStartPath": null,
  "status": null,
  "envAssignees": null,
  "envReviewAssignees": null,
  "dataAssignees": null,
  "dataReviewAssignees": null,
  "statusHistory": null,
  "assignedUserId": null,
  "notes": null,
} satisfies SimulatorConfig

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SimulatorConfig
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


