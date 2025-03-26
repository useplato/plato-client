import { Plato, PlatoClientError } from '../src/index';
import { chromium, Browser } from 'playwright';

async function main() {
  let browser: Browser | undefined;
  try {
    // User needs to provide API key
    const apiKey = 'YOUR_API_KEY_HERE'; // Replace with actual API key
    
    // Initialize the client with required API key
    const plato = new Plato(apiKey);

    // Create a new environment
    console.log('Creating environment...');
    const env = await plato.makeEnvironment('browser-automation-example');
    console.log('Environment created with ID:', env.id);

    // Wait for the environment to be ready
    console.log('Waiting for environment to be ready...');
    await env.waitForReady(300_000); // 5 minutes timeout
    console.log('Environment is ready');

    // Connect with Playwright using the helper
    console.log('Connecting to browser...');
    const { browser: playwrightBrowser, context, page } = await env.connectWithPlaywright(chromium);
    browser = playwrightBrowser; // Store in outer scope for cleanup

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

    // Perform some actions (example)
    console.log('Performing actions...');
    await page.click('a');
    await page.waitForLoadState('networkidle');
    console.log('Clicked link and page loaded');

    // We don't need to manually send heartbeats anymore - it's handled automatically
    console.log('Environment will stay alive due to automatic heartbeats');
    
    // Simulate work (wait for 30 seconds)
    await new Promise(resolve => setTimeout(resolve, 30000));

    // Cleanup - closing the environment will also stop the heartbeat
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
    // Use process.exit if running in Node.js environment
    if (typeof process !== 'undefined') {
      process.exit(1);
    }
  } finally {
    if (browser) {
      await browser.close().catch(console.error);
    }
  }
}

// Run the example
main().catch(console.error); 