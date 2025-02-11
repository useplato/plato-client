# Plato Client


### Run evaluation dataset

```typescript
import Plato from 'plato-cli';

const plato = await Plato.init('cool-agent-123');

const dataset = await plato.loadDataset({ name: 'webvoyager' })

const results = await plato.evaluate({
  dataset,
  run: async (testCase, simulationSession) => {
    const agent = await CoolAgent.init({ cdpUrl: simulationSession.cdpUrl })
    const output = await agent.start({
      startUrl: testCase.startUrl,
      prompt: testCase.prompt,
      outputSchema: testCase.outputSchema, // optional JSON Schema for output structure
    });
    return output;
  },
})

```

