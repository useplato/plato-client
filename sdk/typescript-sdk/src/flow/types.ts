/**
 * Flow execution types for Plato simulator testing.
 * Provides type safety for flow definitions and steps.
 */

/**
 * Base flow step interface that all specific flow steps extend.
 */
export interface BaseFlowStep {
  type: string;
  description?: string;
  timeout?: number; // Timeout in milliseconds
  retries?: number; // Number of times to retry on failure
  retryDelayMs?: number; // Delay between retries in milliseconds
}

/**
 * Wait for a CSS selector to be present.
 */
export interface WaitForSelectorStep extends BaseFlowStep {
  type: 'wait_for_selector';
  selector: string;
}

/**
 * Click on an element.
 */
export interface ClickStep extends BaseFlowStep {
  type: 'click';
  selector: string;
}

/**
 * Fill an input field.
 */
export interface FillStep extends BaseFlowStep {
  type: 'fill';
  selector: string;
  value: string | number | boolean;
}

/**
 * Wait for a specified duration.
 */
export interface WaitStep extends BaseFlowStep {
  type: 'wait';
  duration: number; // Duration to wait in milliseconds
}

/**
 * Navigate to a URL.
 */
export interface NavigateStep extends BaseFlowStep {
  type: 'navigate';
  url: string;
}

/**
 * Wait for URL to contain specific text.
 */
export interface WaitForUrlStep extends BaseFlowStep {
  type: 'wait_for_url';
  urlContains: string;
}

/**
 * Check if an element exists.
 */
export interface CheckElementStep extends BaseFlowStep {
  type: 'check_element';
  selector: string;
  shouldExist?: boolean; // Whether element should exist (default: true)
}

/**
 * Take a screenshot.
 */
export interface ScreenshotStep extends BaseFlowStep {
  type: 'screenshot';
  filename: string;
  fullPage?: boolean; // Take full page screenshot (default: false)
}

/**
 * Verify text appears on the page.
 */
export interface VerifyTextStep extends BaseFlowStep {
  type: 'verify_text';
  text: string;
  shouldExist?: boolean; // Whether text should exist (default: true)
}

/**
 * Verify the current URL.
 */
export interface VerifyUrlStep extends BaseFlowStep {
  type: 'verify_url';
  url: string;
  contains?: boolean; // Whether to use contains matching (default: true)
}

/**
 * Verify no error indicators are present.
 */
export interface VerifyNoErrorsStep extends BaseFlowStep {
  type: 'verify_no_errors';
  errorSelectors?: string[]; // Selectors for error elements
}

/**
 * Generic verification step with subtypes.
 */
export interface VerifyStep extends BaseFlowStep {
  type: 'verify';
  verifyType: 'element_exists' | 'element_visible' | 'element_text' | 'element_count' | 'page_title';
  selector?: string; // CSS selector (for element verifications)
  text?: string; // Expected text
  contains?: boolean; // Whether to use contains matching (default: true)
  count?: number; // Expected element count
  title?: string; // Expected page title
}

/**
 * Union type of all possible flow steps.
 */
export type FlowStep =
  | WaitForSelectorStep
  | ClickStep
  | FillStep
  | WaitStep
  | NavigateStep
  | WaitForUrlStep
  | CheckElementStep
  | ScreenshotStep
  | VerifyTextStep
  | VerifyUrlStep
  | VerifyNoErrorsStep
  | VerifyStep;

/**
 * Flow configuration with validation.
 */
export interface Flow {
  name: string;
  description?: string;
  steps: FlowStep[];
}

/**
 * Logger interface for flow execution.
 */
export interface FlowLogger {
  info(message: string): void;
  error(message: string): void;
  warn?(message: string): void;
  debug?(message: string): void;
}

/**
 * Default console logger implementation.
 */
export class ConsoleLogger implements FlowLogger {
  info(message: string): void {
    console.log(message);
  }

  error(message: string): void {
    console.error(message);
  }

  warn(message: string): void {
    console.warn(message);
  }

  debug(message: string): void {
    console.debug(message);
  }
}

