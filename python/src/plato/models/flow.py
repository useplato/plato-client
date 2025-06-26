"""
Pydantic models for Plato test framework.
Provides type safety and validation for all test data structures.
"""

from typing import Dict, List, Optional, Any, Union, Literal
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, validator, field_validator, model_validator
from abc import ABC
import time


# ============================================================================
# Flow Step Models with Inheritance
# ============================================================================

class FlowStep(BaseModel, ABC):
    """Base flow step class that all specific flow steps inherit from."""
    action: str = Field(..., description="Action type")
    description: Optional[str] = Field(default=None, description="Step description")
    timeout: int = Field(default=10000, description="Timeout in milliseconds")

    class Config:
        extra = "forbid"  # Don't allow extra fields


class WaitForSelectorStep(FlowStep):
    """Wait for a CSS selector to be present."""
    action: Literal["wait_for_selector"] = "wait_for_selector"
    selector: str = Field(..., description="CSS selector to wait for")


class ClickStep(FlowStep):
    """Click on an element."""
    action: Literal["click"] = "click"
    selector: str = Field(..., description="CSS selector to click")


class FillStep(FlowStep):
    """Fill an input field."""
    action: Literal["fill"] = "fill"
    selector: str = Field(..., description="CSS selector for input field")
    value: Union[str, int, bool] = Field(..., description="Value to fill")


class WaitStep(FlowStep):
    """Wait for a specified duration."""
    action: Literal["wait"] = "wait"
    duration: int = Field(..., description="Duration to wait in milliseconds")


class NavigateStep(FlowStep):
    """Navigate to a URL."""
    action: Literal["navigate"] = "navigate"
    url: str = Field(..., description="URL to navigate to")


class WaitForUrlStep(FlowStep):
    """Wait for URL to contain specific text."""
    action: Literal["wait_for_url"] = "wait_for_url"
    url_contains: str = Field(..., description="URL substring to wait for")


class CheckElementStep(FlowStep):
    """Check if an element exists."""
    action: Literal["check_element"] = "check_element"
    selector: str = Field(..., description="CSS selector to check")
    should_exist: bool = Field(default=True, description="Whether element should exist")


class ScreenshotStep(FlowStep):
    """Take a screenshot."""
    action: Literal["screenshot"] = "screenshot"
    filename: str = Field(..., description="Screenshot filename")
    full_page: bool = Field(default=False, description="Take full page screenshot")


class VerifyTextStep(FlowStep):
    """Verify text appears on the page."""
    action: Literal["verify_text"] = "verify_text"
    text: str = Field(..., description="Text to verify")
    should_exist: bool = Field(default=True, description="Whether text should exist")


class VerifyUrlStep(FlowStep):
    """Verify the current URL."""
    action: Literal["verify_url"] = "verify_url"
    url: str = Field(..., description="Expected URL")
    contains: bool = Field(default=True, description="Whether to use contains matching")


class VerifyNoErrorsStep(FlowStep):
    """Verify no error indicators are present."""
    action: Literal["verify_no_errors"] = "verify_no_errors"
    error_selectors: List[str] = Field(default_factory=lambda: [
        ".error", ".alert-danger", ".alert-error",
        "[role='alert']", ".error-message", ".validation-error"
    ], description="Selectors for error elements")


class VerifyStep(FlowStep):
    """Generic verification step with subtypes."""
    action: Literal["verify"] = "verify"
    type: Literal["element_exists", "element_visible", "element_text", "element_count", "page_title"] = Field(..., description="Verification type")
    selector: Optional[str] = Field(default=None, description="CSS selector (for element verifications)")
    text: Optional[str] = Field(default=None, description="Expected text")
    contains: bool = Field(default=True, description="Whether to use contains matching")
    count: Optional[int] = Field(default=None, description="Expected element count")
    title: Optional[str] = Field(default=None, description="Expected page title")

    @model_validator(mode='after')
    def validate_verify_fields(self):
        verify_type = self.type
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
    action = step_data.get("action")
    if not action:
        raise ValueError("Action is required for flow step")
    if action not in FLOW_STEP_TYPES:
        raise ValueError(f"Unknown flow step action: {action}")
    
    step_class = FLOW_STEP_TYPES[action]
    return step_class.parse_obj(step_data)


# ============================================================================
# Configuration Models
# ============================================================================

class Dataset(BaseModel):
    """Dataset configuration with validation."""
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(default=None, description="Dataset description")
    variables: Dict[str, str] = Field(default_factory=dict, description="Dataset variables for flow substitution")
    flows: Optional[List[str]] = Field(default=None, description="Specific flows accessible to this dataset (default: all flows)")
    blocked_flows: Optional[List[str]] = Field(default=None, description="Flows explicitly blocked for this dataset")


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
    

class Simulator(BaseModel):
    """Complete simulator configuration with validation."""
    name: str = Field(..., description="Simulator name")
    reset_timeout: int = Field(default=60000, description="Reset timeout in milliseconds")
    environment_ready_timeout: int = Field(default=300000, description="Environment ready timeout in milliseconds")
    datasets: List[Dataset] = Field(default_factory=list, description="Available datasets")
    flows: List[Flow] = Field(default_factory=list, description="Available flows")

# ============================================================================
# Pattern Step Models
# ============================================================================

class PatternStep(BaseModel, ABC):
    """Base pattern step class that all specific pattern steps inherit from."""
    step_type: str = Field(..., description="Step type")
    
    class Config:
        extra = "allow"  # Allow additional fields for subclasses


class RunStep(PatternStep):
    """Run environments step."""
    step_type: Literal["run"] = "run"
    environments: int = Field(..., gt=0, description="Number of concurrent environments")
    iterations_per_environment: int = Field(..., gt=0, description="Number of tests per environment")
    connection_type: Literal["cdp", "public_url"] = Field(default="cdp", description="Connection type")
    flows: Optional[List[str]] = Field(default=None, description="Specific flows to test (default: all flows)")
    datasets: Optional[List[str]] = Field(default=None, description="Specific datasets to test (default: all datasets)")


class WaitPatternStep(PatternStep):
    """Wait step for patterns."""
    step_type: Literal["wait"] = "wait"
    duration: int = Field(..., gt=0, description="Duration to wait in milliseconds")


class ParallelSteps(PatternStep):
    """Execute multiple steps in parallel."""
    step_type: Literal["parallel"] = "parallel"
    steps: List["PatternStep"] = Field(..., description="Steps to run in parallel")


# Pattern step type mapping for parsing
PATTERN_STEP_TYPES = {
    "run": RunStep,
    "wait": WaitPatternStep,
    "parallel": ParallelSteps,
}


def parse_pattern_step(step_data: Dict[str, Any]) -> PatternStep:
    """Parse a pattern step dictionary into the appropriate PatternStep subclass."""
    step_type = step_data.get("step_type")
    if not step_type:
        raise ValueError("step_type is required for pattern step")
    if step_type not in PATTERN_STEP_TYPES:
        raise ValueError(f"Unknown pattern step type: {step_type}")
    
    step_class = PATTERN_STEP_TYPES[step_type]
    return step_class.parse_obj(step_data)


class Pattern(BaseModel):
    """Pattern configuration defining execution strategy with steps."""
    name: str = Field(..., description="Pattern name")
    description: Optional[str] = Field(default=None, description="Pattern description")
    steps: List[PatternStep] = Field(..., description="Pattern execution steps")

    @field_validator('steps', mode='before')
    def parse_steps(cls, v):
        """Parse raw step dictionaries into proper PatternStep objects."""
        if isinstance(v, list):
            return [parse_pattern_step(step) if isinstance(step, dict) else step for step in v]
        return v

class TestResult(BaseModel):
    """Individual test result with validation."""
    test_id: str = Field(..., description="Unique test identifier")
    run_session_id: Optional[str] = Field(default=None, description="Run session ID")
    simulator: Optional[Simulator] = Field(default=None, description="Simulator")
    dataset: Optional[Dataset] = Field(default=None, description="Dataset")
    flow: Optional[Flow] = Field(default=None, description="Flow")
    success: bool = Field(..., description="Whether test passed")
    reset_duration: Optional[float] = Field(default=None, description="Reset duration in seconds")
    test_duration: Optional[float] = Field(default=None, description="Test duration in seconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")

class EnvironmentResult(BaseModel):
    """Environment result with validation."""
    simulator: Simulator = Field(..., description="Simulator")
    start_duration: float = Field(..., description="Start duration in seconds")
    average_reset_duration: float = Field(..., description="Average reset duration in seconds")
    test_results: List[TestResult] = Field(..., description="Test results")

# Update forward references for ParallelSteps
ParallelSteps.model_rebuild()

class PatternResult(BaseModel):
    """Pattern result with validation."""
    simulator: Simulator = Field(..., description="Simulator")
    pattern: Pattern = Field(..., description="Pattern")
    environment_results: List[EnvironmentResult] = Field(..., description="Environment results")

class RunResult(BaseModel):
    """Run result with validation."""
    run_id: str = Field(..., description="Run identifier")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    pattern_results: List[PatternResult] = Field(..., description="Pattern results")



