/** This module contains tests for the Plato client, including session management and task execution. */

import Plato from '../src/index';
import { z } from 'zod';

jest.setTimeout(30000);

const Company = z.object({
  name: z.string(),
  description: z.string()
});

const Companies = z.object({
  companies: z.array(Company)
});

describe('Plato Client Tests', () => {
  let session;

  beforeEach(async () => {
    const plato = new Plato('22493513-f909-4fef-8aaf-8af2c46dcf1c', 'http://localhost:25565');
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
    const companies = await session.extract('the companies on the page', Companies);

    console.log(companies);
    // Add assertions based on expected outcomes
  });

  test('should perform a task and extract companies', async () => {
    await session.navigate('https://ycombinator.com/companies');
    const companies = await session.task('extract the companies on the page', Companies);

    console.log(companies);
    // Add assertions based on expected outcomes
  });

  test('should perform a task to add item to cart', async () => {
    await session.task('add chocolate soylent to cart', 'https://www.amazon.com');

    // Add assertions based on expected outcomes
  });
});
