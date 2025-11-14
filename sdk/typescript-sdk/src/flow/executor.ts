/**
 * Flow execution engine for Plato simulator testing.
 * Uses Playwright for browser automation with type safety.
 */

import { Page } from 'playwright';
import { URL } from 'url';
import * as path from 'path';
import * as fs from 'fs';
import {
  Flow,
  FlowStep,
  WaitForSelectorStep,
  ClickStep,
  FillStep,
  WaitStep,
  NavigateStep,
  WaitForUrlStep,
  CheckElementStep,
  ScreenshotStep,
  VerifyTextStep,
  VerifyUrlStep,
  VerifyNoErrorsStep,
  VerifyStep,
  FlowLogger,
  ConsoleLogger
} from './types';

/**
 * Configuration options for FlowExecutor.
 */
export interface FlowExecutorOptions {
  page: Page;
  flow: Flow;
  screenshotsDir?: string;
  logger?: FlowLogger;
}

/**
 * Executes configurable flows for simulator interactions with type safety.
 */
export class FlowExecutor {
  private page: Page;
  private flow: Flow;
  private screenshotsDir?: string;
  private baseUrl?: string;
  private logger: FlowLogger;

  constructor(options: FlowExecutorOptions) {
    this.page = options.page;
    this.flow = options.flow;
    this.screenshotsDir = options.screenshotsDir;
    this.logger = options.logger || new ConsoleLogger();

    if (this.screenshotsDir) {
      // Create screenshots directory if it doesn't exist
      if (!fs.existsSync(this.screenshotsDir)) {
        fs.mkdirSync(this.screenshotsDir, { recursive: true });
      }
    }
  }

  /**
   * Resolve a URL against the base URL if it's relative.
   */
  private resolveUrl(url: string): string {
    // If URL is absolute, return as is
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }

    // If we don't have a base URL yet, get it from the current page
    if (!this.baseUrl && this.page.url()) {
      this.baseUrl = this.page.url();
    }

    // If we have a base URL, join with it
    if (this.baseUrl) {
      try {
        const base = new URL(this.baseUrl);
        return new URL(url, base).href;
      } catch (error) {
        this.logger.error(`Failed to resolve URL: ${url} against base: ${this.baseUrl}`);
        return url;
      }
    }

    // If no base URL available, return original URL
    return url;
  }

  /**
   * Execute the configured flow.
   * 
   * @returns Promise<boolean> - True if flow executed successfully, false otherwise
   */
  async executeFlow(): Promise<boolean> {
    const steps = this.flow.steps;

    this.logger.info(`🔄 Starting flow: ${this.flow.name}`);
    this.logger.info(`📋 Flow description: ${this.flow.description || 'No description'}`);
    this.logger.info(`🎯 Steps to execute: ${steps.length}`);

    try {
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        this.logger.info(`🔸 Step ${i + 1}/${steps.length}: ${step.description || step.type}`);

        const success = await this.executeStep(step);
        if (!success) {
          this.logger.error(`❌ Flow '${this.flow.name}' failed at step ${i + 1}`);
          return false;
        }
      }

      this.logger.info(`✅ Flow '${this.flow.name}' completed successfully`);
      return true;
    } catch (error) {
      this.logger.error(`❌ Flow '${this.flow.name}' failed with exception: ${error}`);
      return false;
    }
  }

  /**
   * Execute a single step in a flow.
   */
  private async executeStep(step: FlowStep): Promise<boolean> {
    const timeout = step.timeout || 10000;

    switch (step.type) {
      case 'wait_for_selector':
        return await this.waitForSelector(step, timeout);
      case 'click':
        return await this.click(step, timeout);
      case 'fill':
        return await this.fill(step, timeout);
      case 'wait':
        return await this.wait(step);
      case 'navigate':
        return await this.navigate(step, timeout);
      case 'wait_for_url':
        return await this.waitForUrl(step, timeout);
      case 'check_element':
        return await this.checkElement(step);
      case 'verify':
        return await this.verify(step, timeout);
      case 'screenshot':
        return await this.screenshot(step);
      case 'verify_text':
        return await this.verifyText(step);
      case 'verify_url':
        return await this.verifyUrl(step);
      case 'verify_no_errors':
        return await this.verifyNoErrors(step);
      default:
        this.logger.error(`❌ Unknown step type: ${(step as any).type}`);
        return false;
    }
  }

  /**
   * Wait for a selector to be present.
   */
  private async waitForSelector(step: WaitForSelectorStep, timeout: number): Promise<boolean> {
    try {
      await this.page.waitForSelector(step.selector, { timeout });
      this.logger.info(`✅ Selector found: ${step.selector}`);
      return true;
    } catch (error) {
      this.logger.error(`❌ Selector not found: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Click an element.
   */
  private async click(step: ClickStep, timeout: number): Promise<boolean> {
    try {
      await this.page.waitForSelector(step.selector, { timeout });
      await this.page.click(step.selector);
      this.logger.info(`✅ Clicked: ${step.selector}`);
      return true;
    } catch (error) {
      this.logger.error(`❌ Failed to click: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Fill an input field.
   */
  private async fill(step: FillStep, timeout: number): Promise<boolean> {
    try {
      await this.page.waitForSelector(step.selector, { timeout });
      await this.page.fill(step.selector, String(step.value));

      // Log value safely (mask passwords)
      const displayValue = step.selector.toLowerCase().includes('password')
        ? '*'.repeat(String(step.value).length)
        : String(step.value);
      this.logger.info(`✅ Filled ${step.selector} with: ${displayValue}`);
      return true;
    } catch (error) {
      this.logger.error(`❌ Failed to fill: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Wait for a specified duration.
   */
  private async wait(step: WaitStep): Promise<boolean> {
    try {
      await this.page.waitForTimeout(step.duration);
      this.logger.info(`✅ Waited ${step.duration}ms`);
      return true;
    } catch (error) {
      this.logger.error(`❌ Wait failed: ${error}`);
      return false;
    }
  }

  /**
   * Navigate to a URL.
   */
  private async navigate(step: NavigateStep, timeout: number): Promise<boolean> {
    try {
      const resolvedUrl = this.resolveUrl(step.url);
      await this.page.goto(resolvedUrl, { timeout });
      this.logger.info(`✅ Navigated to: ${resolvedUrl} (original: ${step.url})`);
      // Update base URL after successful navigation
      this.baseUrl = this.page.url();
      return true;
    } catch (error) {
      this.logger.error(`❌ Navigation failed: ${step.url} - ${error}`);
      return false;
    }
  }

  /**
   * Wait for URL to contain specific text.
   */
  private async waitForUrl(step: WaitForUrlStep, timeout: number): Promise<boolean> {
    try {
      await this.page.waitForFunction(
        (urlContains) => window.location.href.includes(urlContains),
        step.urlContains,
        { timeout }
      );
      this.logger.info(`✅ URL contains: ${step.urlContains}`);
      return true;
    } catch (error) {
      this.logger.error(`❌ URL check failed: ${step.urlContains} - ${error}`);
      return false;
    }
  }

  /**
   * Check if an element exists (non-blocking).
   */
  private async checkElement(step: CheckElementStep): Promise<boolean> {
    try {
      const element = await this.page.$(step.selector);
      const exists = element !== null;
      const shouldExist = step.shouldExist !== undefined ? step.shouldExist : true;

      if (shouldExist && exists) {
        this.logger.info(`✅ Element exists as expected: ${step.selector}`);
        return true;
      } else if (!shouldExist && !exists) {
        this.logger.info(`✅ Element absent as expected: ${step.selector}`);
        return true;
      } else {
        this.logger.error(`❌ Element check failed: ${step.selector} (expected: ${shouldExist}, found: ${exists})`);
        return false;
      }
    } catch (error) {
      this.logger.error(`❌ Element check error: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Verify DOM state using multiple validation criteria.
   */
  private async verify(step: VerifyStep, timeout: number): Promise<boolean> {
    switch (step.verifyType) {
      case 'element_exists':
        return await this.verifyElementExists(step);
      case 'element_visible':
        return await this.verifyElementVisible(step);
      case 'element_text':
        return await this.verifyElementText(step);
      case 'element_count':
        return await this.verifyElementCount(step);
      case 'page_title':
        return await this.verifyPageTitle(step);
      default:
        this.logger.error(`❌ Unknown verification type: ${step.verifyType}`);
        return false;
    }
  }

  /**
   * Verify that an element exists in the DOM.
   */
  private async verifyElementExists(step: VerifyStep): Promise<boolean> {
    try {
      if (!step.selector) {
        this.logger.error('❌ Verification failed: selector is required for element_exists');
        return false;
      }

      const element = await this.page.$(step.selector);
      if (element) {
        this.logger.info(`✅ Verification passed: Element exists - ${step.selector}`);
        return true;
      } else {
        this.logger.error(`❌ Verification failed: Element not found - ${step.selector}`);
        return false;
      }
    } catch (error) {
      this.logger.error(`❌ Verification error: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Verify that an element is visible on the page.
   */
  private async verifyElementVisible(step: VerifyStep): Promise<boolean> {
    try {
      if (!step.selector) {
        this.logger.error('❌ Verification failed: selector is required for element_visible');
        return false;
      }

      const element = await this.page.$(step.selector);
      if (element) {
        const isVisible = await element.isVisible();
        if (isVisible) {
          this.logger.info(`✅ Verification passed: Element is visible - ${step.selector}`);
          return true;
        } else {
          this.logger.error(`❌ Verification failed: Element exists but not visible - ${step.selector}`);
          return false;
        }
      } else {
        this.logger.error(`❌ Verification failed: Element not found - ${step.selector}`);
        return false;
      }
    } catch (error) {
      this.logger.error(`❌ Verification error: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Verify that an element contains specific text.
   */
  private async verifyElementText(step: VerifyStep): Promise<boolean> {
    try {
      if (!step.selector) {
        this.logger.error('❌ Verification failed: selector is required for element_text');
        return false;
      }
      if (!step.text) {
        this.logger.error('❌ Verification failed: text is required for element_text');
        return false;
      }

      const element = await this.page.$(step.selector);
      if (element) {
        const actualText = await element.textContent();
        if (actualText !== null) {
          const contains = step.contains !== undefined ? step.contains : true;

          if (contains) {
            if (actualText.includes(step.text)) {
              this.logger.info(`✅ Verification passed: Text contains '${step.text}' - ${step.selector}`);
              return true;
            } else {
              this.logger.error(`❌ Verification failed: Text '${actualText}' does not contain '${step.text}' - ${step.selector}`);
              return false;
            }
          } else {
            if (step.text === actualText.trim()) {
              this.logger.info(`✅ Verification passed: Text matches exactly '${step.text}' - ${step.selector}`);
              return true;
            } else {
              this.logger.error(`❌ Verification failed: Text '${actualText}' does not match '${step.text}' - ${step.selector}`);
              return false;
            }
          }
        } else {
          this.logger.error(`❌ Verification failed: Element has no text content - ${step.selector}`);
          return false;
        }
      } else {
        this.logger.error(`❌ Verification failed: Element not found - ${step.selector}`);
        return false;
      }
    } catch (error) {
      this.logger.error(`❌ Verification error: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Verify the count of elements matching a selector.
   */
  private async verifyElementCount(step: VerifyStep): Promise<boolean> {
    try {
      if (!step.selector) {
        this.logger.error('❌ Verification failed: selector is required for element_count');
        return false;
      }
      if (step.count === undefined) {
        this.logger.error('❌ Verification failed: count is required for element_count');
        return false;
      }

      const elements = await this.page.$$(step.selector);
      const actualCount = elements.length;

      if (actualCount === step.count) {
        this.logger.info(`✅ Verification passed: Found ${actualCount} elements matching '${step.selector}'`);
        return true;
      } else {
        this.logger.error(`❌ Verification failed: Expected ${step.count} elements, found ${actualCount} - ${step.selector}`);
        return false;
      }
    } catch (error) {
      this.logger.error(`❌ Verification error: ${step.selector} - ${error}`);
      return false;
    }
  }

  /**
   * Verify the page title.
   */
  private async verifyPageTitle(step: VerifyStep): Promise<boolean> {
    try {
      if (!step.title) {
        this.logger.error('❌ Verification failed: title is required for page_title');
        return false;
      }

      const actualTitle = await this.page.title();
      const contains = step.contains !== undefined ? step.contains : true;

      if (contains) {
        if (actualTitle.includes(step.title)) {
          this.logger.info(`✅ Verification passed: Page title contains '${step.title}'`);
          return true;
        } else {
          this.logger.error(`❌ Verification failed: Page title '${actualTitle}' does not contain '${step.title}'`);
          return false;
        }
      } else {
        if (step.title === actualTitle) {
          this.logger.info(`✅ Verification passed: Page title matches exactly '${step.title}'`);
          return true;
        } else {
          this.logger.error(`❌ Verification failed: Page title '${actualTitle}' does not match '${step.title}'`);
          return false;
        }
      }
    } catch (error) {
      this.logger.error(`❌ Verification error: ${error}`);
      return false;
    }
  }

  /**
   * Take a screenshot for visual verification.
   */
  private async screenshot(step: ScreenshotStep): Promise<boolean> {
    try {
      // Add timestamp to filename for chronological sorting
      const timestampMs = Date.now();

      // Extract base name and extension
      let timestampedFilename: string;
      const lastDotIndex = step.filename.lastIndexOf('.');
      if (lastDotIndex !== -1) {
        const name = step.filename.substring(0, lastDotIndex);
        const ext = step.filename.substring(lastDotIndex + 1);
        timestampedFilename = `${timestampMs}_${name}.${ext}`;
      } else {
        timestampedFilename = `${timestampMs}_${step.filename}.png`;
      }

      // Save screenshot to the proper directory
      if (this.screenshotsDir) {
        const screenshotPath = path.join(this.screenshotsDir, timestampedFilename);
        await this.page.screenshot({
          path: screenshotPath,
          fullPage: step.fullPage || false
        });
        this.logger.info(`📸 Screenshot taken: ${step.description || 'Screenshot'} -> ${screenshotPath}`);
      }
      return true;
    } catch (error) {
      this.logger.error(`❌ Screenshot failed: ${error}`);
      return false;
    }
  }

  /**
   * Verify that specific text appears anywhere on the page.
   */
  private async verifyText(step: VerifyTextStep): Promise<boolean> {
    try {
      const pageContent = await this.page.content();
      const textFound = pageContent.includes(step.text);
      const shouldExist = step.shouldExist !== undefined ? step.shouldExist : true;

      if (shouldExist && textFound) {
        this.logger.info(`✅ Verification passed: Text '${step.text}' found on page`);
        return true;
      } else if (!shouldExist && !textFound) {
        this.logger.info(`✅ Verification passed: Text '${step.text}' not found on page (as expected)`);
        return true;
      } else {
        if (shouldExist) {
          this.logger.error(`❌ Verification failed: Text '${step.text}' not found on page`);
        } else {
          this.logger.error(`❌ Verification failed: Text '${step.text}' found on page (should not exist)`);
        }
        return false;
      }
    } catch (error) {
      this.logger.error(`❌ Text verification error: ${error}`);
      return false;
    }
  }

  /**
   * Verify the current URL.
   */
  private async verifyUrl(step: VerifyUrlStep): Promise<boolean> {
    try {
      const currentUrl = this.page.url();
      const contains = step.contains !== undefined ? step.contains : true;

      if (contains) {
        if (currentUrl.includes(step.url)) {
          this.logger.info(`✅ Verification passed: URL contains '${step.url}'`);
          return true;
        } else {
          this.logger.error(`❌ Verification failed: URL '${currentUrl}' does not contain '${step.url}'`);
          return false;
        }
      } else {
        if (step.url === currentUrl) {
          this.logger.info(`✅ Verification passed: URL matches exactly '${step.url}'`);
          return true;
        } else {
          this.logger.error(`❌ Verification failed: URL '${currentUrl}' does not match '${step.url}'`);
          return false;
        }
      }
    } catch (error) {
      this.logger.error(`❌ URL verification error: ${error}`);
      return false;
    }
  }

  /**
   * Verify that no error indicators are present on the page.
   */
  private async verifyNoErrors(step: VerifyNoErrorsStep): Promise<boolean> {
    try {
      const errorsFound: string[] = [];
      const defaultErrorSelectors = [
        '.error',
        '.alert-danger',
        '.alert-error',
        '[role="alert"]',
        '.error-message',
        '.validation-error'
      ];
      const errorSelectors = step.errorSelectors || defaultErrorSelectors;

      for (const selector of errorSelectors) {
        const elements = await this.page.$$(selector);
        for (const element of elements) {
          const isVisible = await element.isVisible();
          if (isVisible) {
            const text = await element.textContent();
            if (text && text.trim()) {
              errorsFound.push(`Error found with selector '${selector}': ${text.trim()}`);
            }
          }
        }
      }

      if (errorsFound.length === 0) {
        this.logger.info('✅ Verification passed: No error indicators found on page');
        return true;
      } else {
        this.logger.error('❌ Verification failed: Error indicators found:');
        for (const error of errorsFound) {
          this.logger.error(`   ${error}`);
        }
        return false;
      }
    } catch (error) {
      this.logger.error(`❌ Error verification failed: ${error}`);
      return false;
    }
  }
}

