/** This module contains tests for the Plato client, including session management and task execution. */

import Plato, { PlatoSession } from '../src/index';
import { z } from 'zod';

jest.setTimeout(30000);


const ResponseFormat = z.object({
  companies: z.array(z.object({
    name: z.string(),
    description: z.string(),
    imgUrl: z.string(),
    tags: z.array(z.string())
  }))
});

describe('Plato Client Tests', async () => {
  const plato = new Plato({ apiKey: 'dea0966d-3fc0-4fa2-a54e-6b24e8a6b0f9', baseUrl: 'http://localhost:25565' });
  let session = new PlatoSession(plato)

  beforeEach(async () => {
    session = await plato.startSession();
  });

  test('should start a session and perform actions', async () => {
    await session.navigate('https://www.amazon.com');
    await session.click('the search bar');
    await session.type('chocolate soylent [Enter]');
    await session.click('the first result');
    await session.click('the "add to cart" button');

    // Add assertions based on expected outcomes
  });

  test('should extract companies from a page', async () => {
    await session.navigate('https://ycombinator.com/companies');
    const companies = await session.extract('the companies on the page', { responseFormat: ResponseFormat });

    console.log(companies);
    expect(Array.isArray(companies.companies)).toBe(true);
    expect(companies.companies.length).toBe(20);
  });

  test('should perform a task and extract companies', async () => {
    await session.navigate('https://ycombinator.com/companies');
    const companies = await session.task('extract the companies on the page', { responseFormat: ResponseFormat });

    console.log(companies);
    expect(Array.isArray(companies.companies)).toBe(true);
    expect(companies.companies.length).toBe(20);
  });

  test('should perform a task to add item to cart', async () => {
    await session.task('add chocolate soylent to cart', { startUrl: 'https://www.amazon.com' });

    // Add assertions based on expected outcomes
  });
});
