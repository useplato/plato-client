"""
Flow execution engine for Plato simulator testing.
Uses Pydantic models for type safety and validation.
"""

import logging
from typing import Optional
from pathlib import Path
import argparse
import asyncio
import os
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from abc import ABC
import yaml
from urllib.parse import urljoin
from playwright.async_api import Browser, Page
from playwright.async_api import async_playwright


"""
Pydantic models for Plato test framework.
Provides type safety and validation for all test data structures.
"""




# ============================================================================
# Flow Step Models with Inheritance
# ============================================================================

class FlowStep(BaseModel, ABC):
    """Base flow step class that all specific flow steps inherit from."""
    type: str = Field(..., description="Step type")
    description: Optional[str] = Field(default=None, description="Step description")
    timeout: int = Field(default=10000, description="Timeout in milliseconds")
    retries: int = Field(default=0, ge=0, description="Number of times to retry on failure")
    retry_delay_ms: int = Field(default=500, ge=0, description="Delay between retries in milliseconds")

    class Config:
        extra = "forbid"  # Don't allow extra fields


class WaitForSelectorStep(FlowStep):
    """Wait for a CSS selector to be present."""
    type: Literal["wait_for_selector"] = "wait_for_selector"
    selector: str = Field(..., description="CSS selector to wait for")


class ClickStep(FlowStep):
    """Click on an element."""
    type: Literal["click"] = "click"
    selector: str = Field(..., description="CSS selector to click")


class FillStep(FlowStep):
    """Fill an input field."""
    type: Literal["fill"] = "fill"
    selector: str = Field(..., description="CSS selector for input field")
    value: Union[str, int, bool] = Field(..., description="Value to fill")


class WaitStep(FlowStep):
    """Wait for a specified duration."""
    type: Literal["wait"] = "wait"
    duration: int = Field(..., description="Duration to wait in milliseconds")


class NavigateStep(FlowStep):
    """Navigate to a URL."""
    type: Literal["navigate"] = "navigate"
    url: str = Field(..., description="URL to navigate to")


class WaitForUrlStep(FlowStep):
    """Wait for URL to contain specific text."""
    type: Literal["wait_for_url"] = "wait_for_url"
    url_contains: str = Field(..., description="URL substring to wait for")


class CheckElementStep(FlowStep):
    """Check if an element exists."""
    type: Literal["check_element"] = "check_element"
    selector: str = Field(..., description="CSS selector to check")
    should_exist: bool = Field(default=True, description="Whether element should exist")


class ScreenshotStep(FlowStep):
    """Take a screenshot."""
    type: Literal["screenshot"] = "screenshot"
    filename: str = Field(..., description="Screenshot filename")
    full_page: bool = Field(default=False, description="Take full page screenshot")


class VerifyTextStep(FlowStep):
    """Verify text appears on the page."""
    type: Literal["verify_text"] = "verify_text"
    text: str = Field(..., description="Text to verify")
    should_exist: bool = Field(default=True, description="Whether text should exist")


class VerifyUrlStep(FlowStep):
    """Verify the current URL."""
    type: Literal["verify_url"] = "verify_url"
    url: str = Field(..., description="Expected URL")
    contains: bool = Field(default=True, description="Whether to use contains matching")


class VerifyNoErrorsStep(FlowStep):
    """Verify no error indicators are present."""
    type: Literal["verify_no_errors"] = "verify_no_errors"
    error_selectors: List[str] = Field(default_factory=lambda: [
        ".error", ".alert-danger", ".alert-error",
        "[role='alert']", ".error-message", ".validation-error"
    ], description="Selectors for error elements")


class VerifyStep(FlowStep):
    """Generic verification step with subtypes."""
    type: Literal["verify"] = "verify"
    verify_type: Literal["element_exists", "element_visible", "element_text", "element_count", "page_title"] = Field(..., description="Verification subtype")
    selector: Optional[str] = Field(default=None, description="CSS selector (for element verifications)")
    text: Optional[str] = Field(default=None, description="Expected text")
    contains: bool = Field(default=True, description="Whether to use contains matching")
    count: Optional[int] = Field(default=None, description="Expected element count")
    title: Optional[str] = Field(default=None, description="Expected page title")

    @model_validator(mode='after')
    def validate_verify_fields(self):
        verify_type = self.verify_type
        if verify_type in ['element_exists', 'element_visible', 'element_text', 'element_count']:
            if not self.selector:
                raise ValueError(f"selector is required for verification type '{verify_type}'")
        if verify_type == 'element_text' and not self.text:
            raise ValueError("text is required for element_text verification")
        if verify_type == 'element_count' and self.count is None:
            raise ValueError("count is required for element_count verification")
        if verify_type == 'page_title' and not self.title:
            raise ValueError("title is required for page_title verification")
        return self


# Flow step type mapping for parsing
FLOW_STEP_TYPES = {
    "wait_for_selector": WaitForSelectorStep,
    "click": ClickStep,
    "fill": FillStep,
    "wait": WaitStep,
    "navigate": NavigateStep,
    "wait_for_url": WaitForUrlStep,
    "check_element": CheckElementStep,
    "screenshot": ScreenshotStep,
    "verify_text": VerifyTextStep,
    "verify_url": VerifyUrlStep,
    "verify_no_errors": VerifyNoErrorsStep,
    "verify": VerifyStep,
}


def parse_flow_step(step_data: Dict[str, Any]) -> FlowStep:
    """Parse a flow step dictionary into the appropriate FlowStep subclass."""
    step_type = step_data.get("type")
    if not step_type:
        raise ValueError("Type is required for flow step")
    if step_type not in FLOW_STEP_TYPES:
        raise ValueError(f"Unknown flow step type: {step_type}")

    step_class = FLOW_STEP_TYPES[step_type]
    return step_class.model_validate(step_data)


# ============================================================================
# Configuration Models
# ============================================================================

class Flow(BaseModel):
    """Flow configuration with validation."""
    name: str = Field(..., description="Flow name")
    description: Optional[str] = Field(default=None, description="Flow description")
    steps: List[FlowStep] = Field(default_factory=list, description="Flow steps")

    @field_validator('steps', mode='before')
    def parse_steps(cls, v):
        """Parse raw step dictionaries into proper FlowStep objects."""
        if isinstance(v, list):
            return [parse_flow_step(step) if isinstance(step, dict) else step for step in v]
        return v





# Set up logger for this module

class FlowExecutor:
    """Executes configurable flows for simulator interactions with Pydantic validation."""

    def __init__(self, page: Page, flow: Flow, screenshots_dir: Optional[Path] = None, logger: logging.Logger = logging.getLogger(__name__)):
        self.page = page
        self.flow = flow
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
                
                self.logger.info(f"🔸 Step {i}/{len(steps)}: {step.description or step.type}")

                try:
                    success = await self._execute_step(step)
                    if not success:
                        raise Exception(f"Flow '{self.flow.name}' failed at step {i}")
                except Exception as e:
                    self.logger.error(f"❌ Step {i} failed with exception: {e}")
                    raise Exception(f"Flow '{self.flow.name}' failed at step {i} with exception: {e}")

            self.logger.info(f"✅ Flow '{self.flow.name}' completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Flow '{self.flow.name}' failed with exception: {e}")
            raise Exception(f"Flow '{self.flow.name}' failed with exception: {e}")

    async def _execute_step(self, step: FlowStep) -> bool:
        """Execute a single step in a flow using type attribute."""
        if step.type == "wait_for_selector":
            return await self._wait_for_selector(step)
        elif step.type == "click":
            return await self._click(step)
        elif step.type == "fill":
            return await self._fill(step)
        elif step.type == "wait":
            return await self._wait(step)
        elif step.type == "navigate":
            return await self._navigate(step)
        elif step.type == "wait_for_url":
            return await self._wait_for_url(step)
        elif step.type == "check_element":
            return await self._check_element(step)
        elif step.type == "verify":
            return await self._verify(step)
        elif step.type == "screenshot":
            return await self._screenshot(step)
        elif step.type == "verify_text":
            return await self._verify_text(step)
        elif step.type == "verify_url":
            return await self._verify_url(step)
        elif step.type == "verify_no_errors":
            return await self._verify_no_errors(step)
        else:
            raise ValueError(f"Unknown step type: {step.type}")

    async def _wait_for_selector(self, step: WaitForSelectorStep) -> bool:
        """Wait for a selector to be present."""
        try:
            await self.page.wait_for_selector(step.selector, timeout=step.timeout)
            self.logger.info(f"✅ Selector found: {step.selector}")
            return True
        except Exception as e:
            raise Exception(f"Failed to wait for selector: {step.selector} - {e}")

    async def _click(self, step: ClickStep) -> bool:
        """Click an element."""
        try:
            await self.page.wait_for_selector(step.selector, timeout=step.timeout)
            await self.page.click(step.selector)
            self.logger.info(f"✅ Clicked: {step.selector}")
            return True
        except Exception as e:
            raise Exception(f"Failed to click: {step.selector} - {e}")

    async def _fill(self, step: FillStep) -> bool:
        """Fill an input field."""
        value = step.value

        try:
            await self.page.wait_for_selector(step.selector, timeout=step.timeout)
            await self.page.fill(step.selector, str(value))

            # Log value safely (mask passwords)
            display_value = "*" * len(str(value)) if "password" in step.selector.lower() else str(value)
            self.logger.info(f"✅ Filled {step.selector} with: {display_value}")
            return True
        except Exception as e:
            raise Exception(f"Failed to fill: {step.selector} - {e}")

    async def _wait(self, step: WaitStep) -> bool:
        """Wait for a specified duration."""
        try:
            await self.page.wait_for_timeout(step.duration)
            self.logger.info(f"✅ Waited {step.duration}ms")
            return True
        except Exception as e:
            raise Exception(f"Failed to wait: {e}")

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
            raise Exception(f"Failed to navigate: {step.url} - {e}")

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
            raise Exception(f"Failed to wait for URL: {step.url_contains} - {e}")

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
                raise Exception(f"Element check failed: {step.selector} (expected: {step.should_exist}, found: {exists})")
        except Exception as e:
            raise Exception(f"Failed to check element: {step.selector} - {e}")

    async def _verify(self, step: VerifyStep) -> bool:
        """Verify DOM state using multiple validation criteria."""
        verification_type = step.verify_type

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
            raise ValueError(f"Unknown verification type: {verification_type}")

    async def _verify_element_exists(self, step: VerifyStep) -> bool:
        """Verify that an element exists in the DOM."""
        try:
            element = await self.page.query_selector(step.selector)
            if element:
                self.logger.info(f"✅ Verification passed: Element exists - {step.selector}")
                return True
            else:
                raise Exception(f"Verification failed: Element not found - {step.selector}")
        except Exception as e:
            raise Exception(f"Failed to verify element exists: {step.selector} - {e}")

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
                    raise Exception(f"Verification failed: Element exists but not visible - {step.selector}")
            else:
                raise Exception(f"Verification failed: Element not found - {step.selector}")
        except Exception as e:
            raise Exception(f"Failed to verify element visible: {step.selector} - {e}")

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
                            raise  Exception(f"Verification failed: Text '{actual_text}' does not contain '{step.text}' - {step.selector}")
                    else:
                        if step.text == actual_text.strip():
                            self.logger.info(f"✅ Verification passed: Text matches exactly '{step.text}' - {step.selector}")
                            return True
                        else:
                            raise Exception(f"Verification failed: Text '{actual_text}' does not match '{step.text}' - {step.selector}")
                else:
                    raise Exception(f"Verification failed: Element has no text content - {step.selector}")
            else:
                raise Exception(f"Verification failed: Element not found - {step.selector}")
        except Exception as e:
            raise Exception(f"Failed to verify element text: {step.selector} - {e}")

    async def _verify_element_count(self, step: VerifyStep) -> bool:
        """Verify the count of elements matching a selector."""
        try:
            elements = await self.page.query_selector_all(step.selector)
            actual_count = len(elements)

            if actual_count == step.count:
                self.logger.info(f"✅ Verification passed: Found {actual_count} elements matching '{step.selector}'")
                return True
            else:
                raise Exception(f"Verification failed: Expected {step.count} elements, found {actual_count} - {step.selector}")
        except Exception as e:
            raise Exception(f"Failed to verify element count: {step.selector} - {e}")

    async def _verify_page_title(self, step: VerifyStep) -> bool:
        """Verify the page title."""
        try:
            actual_title = await self.page.title()

            if step.contains:
                if step.title in actual_title:
                    self.logger.info(f"✅ Verification passed: Page title contains '{step.title}'")
                    return True
                else:
                    raise Exception(f"Verification failed: Page title '{actual_title}' does not contain '{step.title}'")
            else:
                if step.title == actual_title:
                    self.logger.info(f"✅ Verification passed: Page title matches exactly '{step.title}'")
                    return True
                else:
                    raise Exception(f"Verification failed: Page title '{actual_title}' does not match '{step.title}'")
        except Exception as e:
            raise Exception(f"Failed to verify page title: {e}")

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
            raise Exception(f"Failed to take screenshot: {e}")

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
                    raise Exception(f"Verification failed: Text '{step.text}' not found on page")
                else:
                    raise Exception(f"Verification failed: Text '{step.text}' found on page (should not exist)")
        except Exception as e:
            raise Exception(f"Failed to verify text: {e}")

    async def _verify_url(self, step: VerifyUrlStep) -> bool:
        """Verify the current URL."""
        try:
            current_url = self.page.url

            if step.contains:
                if step.url in current_url:
                    self.logger.info(f"✅ Verification passed: URL contains '{step.url}'")
                    return True
                else:
                    raise Exception(f"Verification failed: URL '{current_url}' does not contain '{step.url}'")
            else:
                if step.url == current_url:
                    self.logger.info(f"✅ Verification passed: URL matches exactly '{step.url}'")
                    return True
                else:
                    raise Exception(f"Verification failed: URL '{current_url}' does not match '{step.url}'")
        except Exception as e:
            raise Exception(f"Failed to verify URL: {e}")

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
                raise Exception(f"Verification failed: Error indicators found: {errors_found}")
        except Exception as e:
            raise Exception(f"Failed to verify no errors: {e}")


def main():
    parser = argparse.ArgumentParser(description="Plato Flow Executor")
    parser.add_argument("--flow-file", type=str, required=True, help="Path to the flow YAML or JSON file to execute")
    parser.add_argument("--url", type=str, required=True, help="URL to navigate to")
    parser.add_argument("--flow-name", type=str,  help="Name of the flow to execute", default="login")

    args = parser.parse_args()

    if not os.path.exists(args.flow_file):
        raise FileNotFoundError(f"Flow file not found: {args.flow_file}")

    with open(args.flow_file, 'r') as f:
        flow_dict = yaml.safe_load(f)

    flow = next((Flow.model_validate(flow) for flow in flow_dict.get("flows", []) if flow.get("name") == args.flow_name), None)
    if not flow:
        raise ValueError(f"Flow named '{args.flow_name}' not found in {args.flow_file}")

    screenshots_dir = os.path.join(os.path.dirname(args.flow_file), "screenshots")

    async def run_flow():
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(args.url)
                executor = FlowExecutor(page, flow, Path(screenshots_dir))
                result = await executor.execute_flow()
                await browser.close()
                return result
        except Exception as e:
            raise Exception(f"Flow execution failed: {e}")
        finally:
            if browser:
                await browser.close()

    asyncio.run(run_flow())

if __name__ == "__main__":
    main()
