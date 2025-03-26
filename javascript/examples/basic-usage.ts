import { Plato, PlatoClientError } from '../src/index';

async function main() {
  try {
    // User needs to provide API key
    const apiKey = 'YOUR_API_KEY_HERE'; // Replace with actual API key
    
    // Initialize the client with required API key
    const plato = new Plato(apiKey);

    // Create a new environment
    console.log('Creating environment...');
    const env = await plato.makeEnvironment('doordash');
    console.log('Environment created with ID:', env.id);

    // Wait for the environment to be ready
    console.log('Waiting for environment to be ready');
    await env.waitForReady(300_000); // 5 minutes in ms
    console.log('Environment ready');

    // Reset the environment
    console.log('Resetting environment...');
    await env.reset();
    console.log('Environment reset');

    // Get CDP URL
    console.log('Getting CDP URL...');
    const cdpUrl = await env.getCdpUrl();
    console.log('CDP URL:', cdpUrl);

    // Get environment status
    console.log('Checking environment status...');
    const status = await env.getStatus();
    console.log('Environment status:', status);

    // Wait for worker to be ready
    console.log('Waiting for worker...');
    const workerStatus = await plato.getWorkerReady(env.id);
    if (workerStatus.ready) {
      console.log('Worker is ready');
      
      // Get live view URL
      const liveViewUrl = await env.getLiveViewUrl();
      console.log('Live View URL:', liveViewUrl);
    }

    // Note: Heartbeats are sent automatically by the environment
    console.log('Heartbeats are being sent automatically every 30 seconds');

    // Simulate some work
    console.log('Simulating work for 60 seconds...');
    await new Promise(resolve => setTimeout(resolve, 60000));

    // Cleanup - this will also stop the heartbeat interval
    console.log('Closing environment...');
    await env.close();
    console.log('Environment closed');

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
  }
}

// Run the example
main().catch(console.error); 