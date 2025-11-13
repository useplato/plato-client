
# MakeEnvRequest2


## Properties

Name | Type
------------ | -------------
`interfaceType` | string
`interfaceWidth` | number
`interfaceHeight` | number
`source` | string
`openPageOnStart` | boolean
`envId` | string
`envConfig` | { [key: string]: any; }
`recordNetworkRequests` | boolean
`recordActions` | boolean
`loadChromeExtensions` | Array&lt;string&gt;
`keepalive` | boolean
`alias` | string
`fast` | boolean
`version` | string
`tag` | string
`dataset` | string
`artifactId` | string
`timeout` | number

## Example

```typescript
import type { MakeEnvRequest2 } from '@plato-ai/sdk'

// TODO: Update the object below with actual values
const example = {
  "interfaceType": null,
  "interfaceWidth": null,
  "interfaceHeight": null,
  "source": null,
  "openPageOnStart": null,
  "envId": null,
  "envConfig": null,
  "recordNetworkRequests": null,
  "recordActions": null,
  "loadChromeExtensions": null,
  "keepalive": null,
  "alias": null,
  "fast": null,
  "version": null,
  "tag": null,
  "dataset": null,
  "artifactId": null,
  "timeout": null,
} satisfies MakeEnvRequest2

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MakeEnvRequest2
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


