"""
Pydantic models for Plato test framework.
Provides type safety and validation for all test data structures.
"""

from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from abc import ABC


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
    return step_class.parse_obj(step_data)


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



