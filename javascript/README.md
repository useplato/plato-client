# Plato Client


```typescript
import Plato from 'plato-cli';
import { z } from 'zod';

const plato = new Plato({ apiKey: 'YOUR_PLATO_API_KEY' });

const session = await plato.startSession();

const ResponseFormat = z.object({
  companies: z.array(z.object({
    name: z.string(),
    description: z.string(),
    imgUrl: z.string(),
    tags: z.array(z.string())
  }))
});

await session.navigate('https://ycombinator.com/companies');
const response = await session.extract('all of the companies on the page', { responseFormat: ResponseFormat });

response.companies.forEach((company) => {
  console.log(company.name, company.description, company.imgUrl, company.tags);
})

```

