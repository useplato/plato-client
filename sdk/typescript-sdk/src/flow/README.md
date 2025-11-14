# Flow Executor

The Flow Executor provides a powerful way to define and execute browser automation flows using Playwright. This is particularly useful for testing simulator interactions in the Plato platform.

## Installation

First, install Playwright as a peer dependency:

```bash
npm install playwright
# or
yarn add playwright
```

## Basic Usage

```typescript
import { chromium } from 'playwright';
import { FlowExecutor, Flow } from '@plato-ai/sdk';

async function runFlow() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  const flow: Flow = {
    name: 'login',
    description: 'Login to the application',
    steps: [
      {
        type: 'navigate',
        url: 'https://example.com/login',
        description: 'Navigate to login page'
      },
      {
        type: 'fill',
        selector: '#username',
        value: 'testuser',
        description: 'Fill username'
      },
      {
        type: 'fill',
        selector: '#password',
        value: 'password123',
        description: 'Fill password'
      },
      {
        type: 'click',
        selector: 'button[type="submit"]',
        description: 'Click login button'
      },
      {
        type: 'wait_for_url',
        urlContains: '/dashboard',
        description: 'Wait for redirect to dashboard'
      },
      {
        type: 'verify',
        verifyType: 'page_title',
        title: 'Dashboard',
        contains: true,
        description: 'Verify we are on the dashboard'
      }
    ]
  };

  const executor = new FlowExecutor({
    page,
    flow,
    screenshotsDir: './screenshots'
  });

  const success = await executor.executeFlow();
  console.log(`Flow ${success ? 'succeeded' : 'failed'}`);

  await browser.close();
}

runFlow();
```

## Flow Step Types

### Navigation Steps

#### `navigate`
Navigate to a URL.

```typescript
{
  type: 'navigate',
  url: 'https://example.com',
  description: 'Navigate to homepage'
}
```

#### `wait_for_url`
Wait for URL to contain specific text.

```typescript
{
  type: 'wait_for_url',
  urlContains: '/dashboard',
  timeout: 5000
}
```

### Interaction Steps

#### `click`
Click on an element.

```typescript
{
  type: 'click',
  selector: 'button.submit',
  description: 'Click submit button'
}
```

#### `fill`
Fill an input field.

```typescript
{
  type: 'fill',
  selector: '#email',
  value: 'user@example.com',
  description: 'Fill email field'
}
```

### Wait Steps

#### `wait`
Wait for a specified duration.

```typescript
{
  type: 'wait',
  duration: 2000, // milliseconds
  description: 'Wait for animation'
}
```

#### `wait_for_selector`
Wait for a selector to be present.

```typescript
{
  type: 'wait_for_selector',
  selector: '.loading-spinner',
  timeout: 10000
}
```

### Verification Steps

#### `verify`
Generic verification with multiple subtypes:

**Element Exists**
```typescript
{
  type: 'verify',
  verifyType: 'element_exists',
  selector: '.success-message'
}
```

**Element Visible**
```typescript
{
  type: 'verify',
  verifyType: 'element_visible',
  selector: '.modal'
}
```

**Element Text**
```typescript
{
  type: 'verify',
  verifyType: 'element_text',
  selector: '.welcome-message',
  text: 'Welcome back',
  contains: true
}
```

**Element Count**
```typescript
{
  type: 'verify',
  verifyType: 'element_count',
  selector: '.list-item',
  count: 5
}
```

**Page Title**
```typescript
{
  type: 'verify',
  verifyType: 'page_title',
  title: 'Dashboard',
  contains: true
}
```

#### `verify_text`
Verify text appears anywhere on the page.

```typescript
{
  type: 'verify_text',
  text: 'Success!',
  shouldExist: true
}
```

#### `verify_url`
Verify the current URL.

```typescript
{
  type: 'verify_url',
  url: '/dashboard',
  contains: true
}
```

#### `verify_no_errors`
Verify no error indicators are present.

```typescript
{
  type: 'verify_no_errors',
  errorSelectors: ['.error', '.alert-danger', '[role="alert"]']
}
```

#### `check_element`
Check if an element exists (non-blocking).

```typescript
{
  type: 'check_element',
  selector: '.optional-banner',
  shouldExist: false
}
```

### Utility Steps

#### `screenshot`
Take a screenshot for visual verification.

```typescript
{
  type: 'screenshot',
  filename: 'dashboard.png',
  fullPage: true,
  description: 'Capture dashboard state'
}
```

## Custom Logger

You can provide a custom logger implementation:

```typescript
import { FlowLogger } from '@plato-ai/sdk';

class CustomLogger implements FlowLogger {
  info(message: string): void {
    // Custom info logging
  }

  error(message: string): void {
    // Custom error logging
  }

  warn(message: string): void {
    // Custom warning logging
  }

  debug(message: string): void {
    // Custom debug logging
  }
}

const executor = new FlowExecutor({
  page,
  flow,
  logger: new CustomLogger()
});
```

## Complete Example with Error Handling

```typescript
import { chromium } from 'playwright';
import { FlowExecutor, Flow } from '@plato-ai/sdk';

async function runCompleteFlow() {
  let browser;
  try {
    browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    const flow: Flow = {
      name: 'e2e-test',
      description: 'End-to-end test flow',
      steps: [
        {
          type: 'navigate',
          url: 'https://example.com',
          description: 'Navigate to homepage'
        },
        {
          type: 'screenshot',
          filename: 'homepage.png',
          fullPage: true,
          description: 'Capture homepage'
        },
        {
          type: 'verify',
          verifyType: 'page_title',
          title: 'Example Domain',
          contains: false,
          description: 'Verify page title'
        },
        {
          type: 'verify_no_errors',
          description: 'Ensure no errors on page'
        }
      ]
    };

    const executor = new FlowExecutor({
      page,
      flow,
      screenshotsDir: './test-screenshots'
    });

    const success = await executor.executeFlow();
    
    if (success) {
      console.log('✅ Flow completed successfully');
    } else {
      console.error('❌ Flow failed');
      process.exit(1);
    }
  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

runCompleteFlow();
```

## Features

- ✅ Type-safe flow definitions with TypeScript
- ✅ Comprehensive step types for common browser interactions
- ✅ Built-in verification and validation steps
- ✅ Automatic screenshot capture with timestamps
- ✅ Customizable logging
- ✅ Relative URL resolution
- ✅ Password masking in logs
- ✅ Detailed error messages

## Notes

- All timeouts are in milliseconds (default: 10000ms)
- Screenshots are automatically timestamped for chronological sorting
- Passwords in selectors containing "password" are automatically masked in logs
- The flow executor is protected from OpenAPI generator overwrites

