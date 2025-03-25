# Plato Client Examples

This directory contains example scripts demonstrating how to use the Plato client library.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Set up your environment variables:
```bash
# Create a .env file in the root directory
echo "PLATO_API_KEY=your_api_key" > ../.env
```

## Running Examples

You can run the examples using `ts-node` through the npm script:

```bash
# Run basic usage example
npm run examples examples/basic-usage.ts

# Run browser automation example
npm run examples examples/browser-automation.ts
```

## Available Examples

### 1. Basic Usage (`basic-usage.ts`)
Demonstrates the basic functionality of the Plato client:
- Creating an environment
- Getting CDP URL
- Checking environment status
- Managing worker lifecycle
- Using heartbeats to keep the environment alive
- Proper cleanup

### 2. Browser Automation (`browser-automation.ts`)
Shows how to use the Plato client with Playwright for browser automation:
- Setting up a browser environment
- Connecting Playwright to the CDP endpoint
- Basic web automation tasks (navigation, screenshots, content extraction)
- Proper error handling and cleanup

## Notes

- Make sure you have a valid Plato API key before running the examples
- The browser automation example requires Playwright, which is included in the devDependencies
- Examples include proper error handling and cleanup to demonstrate best practices
- Each example can be run independently and includes console output to show what's happening

## Troubleshooting

If you encounter any issues:

1. Verify your API key is correct
2. Check that all dependencies are installed
3. Make sure you're running the latest version of the client
4. Check the console output for error messages

For more detailed information, refer to the main [README](../README.md) in the root directory. 