"""
Flow execution engine for Plato simulator testing.
Uses Pydantic models for type safety and validation.
"""

import logging
from typing import Optional
from pathlib import Path
import sys
import os
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import Page
from plato.models.flow import (
    FlowStep, Dataset, Flow,
    WaitForSelectorStep, ClickStep, FillStep, WaitStep, NavigateStep,
    WaitForUrlStep, CheckElementStep, ScreenshotStep, VerifyTextStep,
    VerifyUrlStep, VerifyNoErrorsStep, VerifyStep
)

# Set up logger for this module

class FlowExecutor:
    """Executes configurable flows for simulator interactions with Pydantic validation."""

    def __init__(self, page: Page, flow: Flow, dataset: Dataset, screenshots_dir: Optional[Path] = None, logger: logging.Logger = logging.getLogger(__name__)):
        self.page = page
        self.flow = flow
        self.dataset = dataset
        self.screenshots_dir = screenshots_dir
        if self.screenshots_dir:
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = None  # Will be set from the page URL after first navigation
        self.logger = logger

    def _resolve_url(self, url: str) -> str:
        """Resolve a URL against the base URL if it's relative."""
        # If URL is absolute, return as is
        if url.startswith(('http://', 'https://')):
            return url

        # If we don't have a base URL yet, get it from the current page
        if not self.base_url and self.page.url:
            self.base_url = self.page.url

        # If we have a base URL, join with it
        if self.base_url:
            return urljoin(self.base_url, url)

        # If no base URL available, return original URL
        return url

    async def execute_flow(self) -> bool:
        """
        Execute a named flow from the configuration.

        Args:
            flow_name: Name of the flow to execute (e.g., 'login', 'logout', 'create_project')

        Returns:
            bool: True if flow executed successfully, False otherwise
        """

        steps = self.flow.steps

        self.logger.info(f"🔄 Starting flow: {self.flow.name}")
        self.logger.info(f"📋 Flow description: {self.flow.description or 'No description'}")
        self.logger.info(f"🎯 Steps to execute: {len(steps)}")

        try:
            for i, step in enumerate(steps, 1):
                self.logger.info(f"🔸 Step {i}/{len(steps)}: {step.description or step.action}")

                success = await self._execute_step(step)
                if not success:
                    self.logger.error(f"❌ Flow '{self.flow.name}' failed at step {i}")
                    return False

            self.logger.info(f"✅ Flow '{self.flow.name}' completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Flow '{self.flow.name}' failed with exception: {e}")
            return False

    async def _execute_step(self, step: FlowStep) -> bool:
        """Execute a single step in a flow using action attribute."""
        if step.action == "wait_for_selector":
            return await self._wait_for_selector(step)
        elif step.action == "click":
            return await self._click(step)
        elif step.action == "fill":
            return await self._fill(step)
        elif step.action == "wait":
            return await self._wait(step)
        elif step.action == "navigate":
            return await self._navigate(step)
        elif step.action == "wait_for_url":
            return await self._wait_for_url(step)
        elif step.action == "check_element":
            return await self._check_element(step)
        elif step.action == "verify":
            return await self._verify(step)
        elif step.action == "screenshot":
            return await self._screenshot(step)
        elif step.action == "verify_text":
            return await self._verify_text(step)
        elif step.action == "verify_url":
            return await self._verify_url(step)
        elif step.action == "verify_no_errors":
            return await self._verify_no_errors(step)
        else:
            self.logger.error(f"❌ Unknown step action: {step.action}")
            return False

    async def _wait_for_selector(self, step: WaitForSelectorStep) -> bool:
        """Wait for a selector to be present."""
        try:
            await self.page.wait_for_selector(step.selector, timeout=step.timeout)
            self.logger.info(f"✅ Selector found: {step.selector}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Selector not found: {step.selector} - {e}")
            return False

    async def _click(self, step: ClickStep) -> bool:
        """Click an element."""
        try:
            await self.page.wait_for_selector(step.selector, timeout=step.timeout)
            await self.page.click(step.selector)
            self.logger.info(f"✅ Clicked: {step.selector}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to click: {step.selector} - {e}")
            return False

    async def _fill(self, step: FillStep) -> bool:
        """Fill an input field."""
        value_ref = step.value

        # Resolve value from dataset variables if it's a reference
        if isinstance(value_ref, str) and value_ref.startswith("$"):
            variable_key = value_ref[1:]  # Remove $ prefix
            value = self.dataset.variables.get(variable_key)
            if value is None:
                self.logger.error(f"❌ Dataset variable '{variable_key}' not found")
                return False
        else:
            value = value_ref

        try:
            await self.page.wait_for_selector(step.selector, timeout=step.timeout)
            await self.page.fill(step.selector, str(value))

            # Log value safely (mask passwords)
            display_value = "*" * len(str(value)) if "password" in step.selector.lower() else str(value)
            self.logger.info(f"✅ Filled {step.selector} with: {display_value}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to fill: {step.selector} - {e}")
            return False

    async def _wait(self, step: WaitStep) -> bool:
        """Wait for a specified duration."""
        try:
            await self.page.wait_for_timeout(step.duration)
            self.logger.info(f"✅ Waited {step.duration}ms")
            return True
        except Exception as e:
            self.logger.error(f"❌ Wait failed: {e}")
            return False

    async def _navigate(self, step: NavigateStep) -> bool:
        """Navigate to a URL."""
        try:
            resolved_url = self._resolve_url(step.url)
            await self.page.goto(resolved_url)
            self.logger.info(f"✅ Navigated to: {resolved_url} (original: {step.url})")
            # Update base URL after successful navigation
            self.base_url = self.page.url
            return True
        except Exception as e:
            self.logger.error(f"❌ Navigation failed: {step.url} - {e}")
            return False

    async def _wait_for_url(self, step: WaitForUrlStep) -> bool:
        """Wait for URL to contain specific text."""
        try:
            await self.page.wait_for_function(
                f"window.location.href.includes('{step.url_contains}')",
                timeout=step.timeout
            )
            self.logger.info(f"✅ URL contains: {step.url_contains}")
            return True
        except Exception as e:
            self.logger.error(f"❌ URL check failed: {step.url_contains} - {e}")
            return False

    async def _check_element(self, step: CheckElementStep) -> bool:
        """Check if an element exists (non-blocking)."""
        try:
            element = await self.page.query_selector(step.selector)
            exists = element is not None

            if step.should_exist and exists:
                self.logger.info(f"✅ Element exists as expected: {step.selector}")
                return True
            elif not step.should_exist and not exists:
                self.logger.info(f"✅ Element absent as expected: {step.selector}")
                return True
            else:
                self.logger.error(f"❌ Element check failed: {step.selector} (expected: {step.should_exist}, found: {exists})")
                return False
        except Exception as e:
            self.logger.error(f"❌ Element check error: {step.selector} - {e}")
            return False

    async def _verify(self, step: VerifyStep) -> bool:
        """Verify DOM state using multiple validation criteria."""
        verification_type = step.type

        if verification_type == "element_exists":
            return await self._verify_element_exists(step)
        elif verification_type == "element_visible":
            return await self._verify_element_visible(step)
        elif verification_type == "element_text":
            return await self._verify_element_text(step)
        elif verification_type == "element_count":
            return await self._verify_element_count(step)
        elif verification_type == "page_title":
            return await self._verify_page_title(step)
        else:
            self.logger.error(f"❌ Unknown verification type: {verification_type}")
            return False

    async def _verify_element_exists(self, step: VerifyStep) -> bool:
        """Verify that an element exists in the DOM."""
        try:
            element = await self.page.query_selector(step.selector)
            if element:
                self.logger.info(f"✅ Verification passed: Element exists - {step.selector}")
                return True
            else:
                self.logger.error(f"❌ Verification failed: Element not found - {step.selector}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Verification error: {step.selector} - {e}")
            return False

    async def _verify_element_visible(self, step: VerifyStep) -> bool:
        """Verify that an element is visible on the page."""
        try:
            element = await self.page.query_selector(step.selector)
            if element:
                is_visible = await element.is_visible()
                if is_visible:
                    self.logger.info(f"✅ Verification passed: Element is visible - {step.selector}")
                    return True
                else:
                    self.logger.error(f"❌ Verification failed: Element exists but not visible - {step.selector}")
                    return False
            else:
                self.logger.error(f"❌ Verification failed: Element not found - {step.selector}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Verification error: {step.selector} - {e}")
            return False

    async def _verify_element_text(self, step: VerifyStep) -> bool:
        """Verify that an element contains specific text."""
        try:
            element = await self.page.query_selector(step.selector)
            if element:
                actual_text = await element.text_content()
                if actual_text:
                    if step.contains:
                        if step.text in actual_text:
                            self.logger.info(f"✅ Verification passed: Text contains '{step.text}' - {step.selector}")
                            return True
                        else:
                            self.logger.error(f"❌ Verification failed: Text '{actual_text}' does not contain '{step.text}' - {step.selector}")
                            return False
                    else:
                        if step.text == actual_text.strip():
                            self.logger.info(f"✅ Verification passed: Text matches exactly '{step.text}' - {step.selector}")
                            return True
                        else:
                            self.logger.error(f"❌ Verification failed: Text '{actual_text}' does not match '{step.text}' - {step.selector}")
                            return False
                else:
                    self.logger.error(f"❌ Verification failed: Element has no text content - {step.selector}")
                    return False
            else:
                self.logger.error(f"❌ Verification failed: Element not found - {step.selector}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Verification error: {step.selector} - {e}")
            return False

    async def _verify_element_count(self, step: VerifyStep) -> bool:
        """Verify the count of elements matching a selector."""
        try:
            elements = await self.page.query_selector_all(step.selector)
            actual_count = len(elements)

            if actual_count == step.count:
                self.logger.info(f"✅ Verification passed: Found {actual_count} elements matching '{step.selector}'")
                return True
            else:
                self.logger.error(f"❌ Verification failed: Expected {step.count} elements, found {actual_count} - {step.selector}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Verification error: {step.selector} - {e}")
            return False

    async def _verify_page_title(self, step: VerifyStep) -> bool:
        """Verify the page title."""
        try:
            actual_title = await self.page.title()

            if step.contains:
                if step.title in actual_title:
                    self.logger.info(f"✅ Verification passed: Page title contains '{step.title}'")
                    return True
                else:
                    self.logger.error(f"❌ Verification failed: Page title '{actual_title}' does not contain '{step.title}'")
                    return False
            else:
                if step.title == actual_title:
                    self.logger.info(f"✅ Verification passed: Page title matches exactly '{step.title}'")
                    return True
                else:
                    self.logger.error(f"❌ Verification failed: Page title '{actual_title}' does not match '{step.title}'")
                    return False
        except Exception as e:
            self.logger.error(f"❌ Verification error: {e}")
            return False

    async def _screenshot(self, step: ScreenshotStep) -> bool:
        """Take a screenshot for visual verification."""
        try:
            # Add timestamp to filename for chronological sorting
            import time
            # Use epoch time in milliseconds for guaranteed chronological sorting
            timestamp_ms = int(time.time() * 1000)

            # Extract base name and extension
            filename = step.filename
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                timestamped_filename = f"{timestamp_ms}_{name}.{ext}"
            else:
                timestamped_filename = f"{timestamp_ms}_{filename}.png"

            # Save screenshot to the proper directory
            if self.screenshots_dir:
                screenshot_path = self.screenshots_dir / timestamped_filename
                await self.page.screenshot(path=str(screenshot_path), full_page=step.full_page)
                self.logger.info(f"📸 Screenshot taken: {step.description or 'Screenshot'} -> {screenshot_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Screenshot failed: {e}")
            return False

    async def _verify_text(self, step: VerifyTextStep) -> bool:
        """Verify that specific text appears anywhere on the page."""
        try:
            page_content = await self.page.content()
            text_found = step.text in page_content

            if step.should_exist and text_found:
                self.logger.info(f"✅ Verification passed: Text '{step.text}' found on page")
                return True
            elif not step.should_exist and not text_found:
                self.logger.info(f"✅ Verification passed: Text '{step.text}' not found on page (as expected)")
                return True
            else:
                if step.should_exist:
                    self.logger.error(f"❌ Verification failed: Text '{step.text}' not found on page")
                else:
                    self.logger.error(f"❌ Verification failed: Text '{step.text}' found on page (should not exist)")
                return False
        except Exception as e:
            self.logger.error(f"❌ Text verification error: {e}")
            return False

    async def _verify_url(self, step: VerifyUrlStep) -> bool:
        """Verify the current URL."""
        try:
            current_url = self.page.url

            if step.contains:
                if step.url in current_url:
                    self.logger.info(f"✅ Verification passed: URL contains '{step.url}'")
                    return True
                else:
                    self.logger.error(f"❌ Verification failed: URL '{current_url}' does not contain '{step.url}'")
                    return False
            else:
                if step.url == current_url:
                    self.logger.info(f"✅ Verification passed: URL matches exactly '{step.url}'")
                    return True
                else:
                    self.logger.error(f"❌ Verification failed: URL '{current_url}' does not match '{step.url}'")
                    return False
        except Exception as e:
            self.logger.error(f"❌ URL verification error: {e}")
            return False

    async def _verify_no_errors(self, step: VerifyNoErrorsStep) -> bool:
        """Verify that no error indicators are present on the page."""
        try:
            errors_found = []

            for selector in step.error_selectors:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.text_content()
                        if text and text.strip():
                            errors_found.append(f"Error found with selector '{selector}': {text.strip()}")

            if not errors_found:
                self.logger.info("✅ Verification passed: No error indicators found on page")
                return True
            else:
                self.logger.error("❌ Verification failed: Error indicators found:")
                for error in errors_found:
                    self.logger.error(f"   {error}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Error verification failed: {e}")
            return False
