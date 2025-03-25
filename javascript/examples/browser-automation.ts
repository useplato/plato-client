import { Plato, PlatoClientError } from '../src/index';
import { chromium, Browser } from 'playwright';
import 'dotenv/config';

async function main() {
  let browser: Browser | undefined;
  try {
    // Initialize the client
    const plato = new Plato(process.env.PLATO_API_KEY);

    // Create a new environment
    console.log('Creating environment...');
    const env = await plato.makeEnvironment('browser-automation-example');
    console.log('Environment created with ID:', env.id);

    // Get CDP URL and connect Playwright
    console.log('Connecting to browser...');
    const cdpUrl = await env.getCdpUrl();
    browser = await chromium.connectOverCDP(cdpUrl);

    // Create a new page
    const page = await browser.newPage();

    // Navigate to a website
    console.log('Navigating to example.com...');
    await page.goto('https://example.com');

    // Take a screenshot
    console.log('Taking screenshot...');
    await page.screenshot({ path: 'example.png' });

    // Get page title
    const title = await page.title();
    console.log('Page title:', title);

    // Extract some content
    const content = await page.textContent('h1');
    console.log('H1 content:', content);

    // Keep the environment alive with heartbeats
    const heartbeatInterval = setInterval(() => {
      plato.sendHeartbeat(env.id).catch(console.error);
    }, 30000);

    // Cleanup
    clearInterval(heartbeatInterval);
    console.log('Closing browser and environment...');
    await browser.close();
    await env.close();
    console.log('Cleanup complete');

  } catch (err) {
    if (err instanceof PlatoClientError) {
      console.error('Plato API Error:', err.message);
    } else if (err instanceof Error) {
      console.error('Unexpected error:', err.message);
    } else {
      console.error('Unknown error:', err);
    }
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close().catch(console.error);
    }
  }
}

// Run the example
main().catch(console.error); 