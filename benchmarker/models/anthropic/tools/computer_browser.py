import asyncio
import base64
from enum import StrEnum
from typing import Literal, TypedDict, cast, get_args, Optional, Dict
from playwright.async_api import Browser as AsyncBrowser, Page as AsyncPage
from playwright.async_api import async_playwright

from anthropic.types.beta import BetaToolComputerUse20241022Param, BetaToolUnionParam
from .base import BaseAnthropicTool, ToolError, ToolResult

Action_20241022 = Literal[
  "key",
  "type",
  "mouse_move",
  "left_click",
  "left_click_drag",
  "right_click",
  "middle_click",
  "double_click",
  "screenshot",
  "cursor_position",
]

Action_20250124 = (
  Action_20241022
  | Literal[
    "left_mouse_down",
    "left_mouse_up",
    "scroll",
    "hold_key",
    "wait",
    "triple_click",
  ]
)

ScrollDirection = Literal["up", "down", "left", "right"]

class Resolution(TypedDict):
  width: int
  height: int

class ScalingSource(StrEnum):
  COMPUTER = "computer"
  API = "api"

class ComputerToolOptions(TypedDict):
  display_height_px: int
  display_width_px: int
  display_number: int | None

class BaseComputerBrowserTool:
  """
  A tool that allows the agent to interact with a browser using Playwright.
  The tool parameters are defined by Anthropic and are not editable.
  """

  name: Literal["computer"] = "computer"
  width: int = 1280  # Default width
  height: int = 720  # Default height
  display_num: int | None = None

  _screenshot_delay = 0.5
  _scaling_enabled = True

  @property
  def options(self) -> ComputerToolOptions:
    width, height = self.scale_coordinates(
      ScalingSource.COMPUTER, self.width, self.height
    )
    return {
      "display_width_px": width,
      "display_height_px": height,
      "display_number": self.display_num,
    }

  def __init__(self, cdp_url: str):
    super().__init__()
    self.cdp_url = cdp_url
    self._browser: Optional[AsyncBrowser] = None
    self._page: Optional[AsyncPage] = None

  def _handle_new_page(self, page: AsyncPage):
    """Handle the creation of a new page."""
    # print(f"New page created: {page.url}")
    self._page = page
    page.on("close", self._handle_page_close)

  def _handle_page_close(self, page: AsyncPage):
    """Handle the closure of a page."""
    # print(f"Page closed: {page.url}")
    if self._page == page:
      if self._browser and self._browser.contexts and self._browser.contexts[0].pages:
        self._page = self._browser.contexts[0].pages[-1]
        print(f"Switched active page to: {self._page.url}")
      else:
        print("Warning: All pages have been closed.")
        self._page = None

  async def __aenter__(self):
    self._playwright_manager = await self._connect_browser()
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self._browser:
      await self._browser.close()
    if self._playwright_manager:
      await self._playwright_manager.stop()

  async def _connect_browser(self):
    playwright = await async_playwright().start()
    self._browser = await playwright.chromium.connect_over_cdp(self.cdp_url)
    if self._browser.contexts:
      context = self._browser.contexts[0]
    else:
      context = await self._browser.new_context(viewport={"width": self.width, "height": self.height})

    # Add event listeners for page creation and closure
    context.on("page", self._handle_new_page)

    if context.pages:
      self._page = context.pages[0]
    else:
      self._page = await context.new_page()

    await self._page.set_viewport_size({"width": self.width, "height": self.height})
    self._page.on("close", self._handle_page_close)

    return playwright

  async def goto(self, url: str):
    if not self._page:
      raise ToolError("Page is not initialized")
    await self._page.goto(url)

  async def screenshot(self) -> ToolResult:
    """Take a screenshot of the current page and return base64 encoded image."""
    if not self._page:
      raise ToolError("Page is not initialized")

    png_bytes = await self._page.screenshot(full_page=False)

    # Create screenshots directory if it doesn't exist
    # os.makedirs("./screenshots", exist_ok=True)

    # with open(f"./screenshots/{str(uuid4())}.png", "wb") as f:
    #   f.write(png_bytes)
    return ToolResult(base64_image=base64.b64encode(png_bytes).decode())

  def validate_and_get_coordinates(self, coordinate: tuple[int, int] | None = None):
    if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
      raise ToolError(f"{coordinate} must be a tuple of length 2")
    if not all(isinstance(i, int) and i >= 0 for i in coordinate):
      raise ToolError(f"{coordinate} must be a tuple of non-negative ints")

    # return self.scale_coordinates(ScalingSource.API, coordinate[0], coordinate[1])
    return coordinate[0], coordinate[1]

  def scale_coordinates(self, source: ScalingSource, x: int, y: int):
    """Scale coordinates based on viewport size."""
    if not self._scaling_enabled:
      return x, y

    # Simple scaling based on viewport size
    x_scale = x / self.width if source == ScalingSource.API else self.width / x
    y_scale = y / self.height if source == ScalingSource.API else self.height / y

    return round(x * x_scale), round(y * y_scale)

  def _map_key(self, key: str) -> str:
    """Map common key names to Playwright key names."""
    key = key.lower()
    # Add function key mapping
    if key.startswith('f') and len(key) <= 3:
      try:
        num = int(key[1:])
        if 1 <= num <= 12:  # F1-F12 are valid
          return f"F{num}"
      except ValueError:
        pass

    key_mapping = {
      "ctrl": "Control",
      "cmd": "Meta",
      "win": "Meta",
      "alt": "Alt",
      "shift": "Shift",
      "esc": "Escape",
      "escape": "Escape",
      "return": "Enter",
      "del": "Delete",
      "delete": "Delete",
      "ins": "Insert",
      "pageup": "PageUp",
      "pagedown": "PageDown",
      "page_down": "PageDown",
      "page_up": "PageUp",
      "home": "Home",
      "end": "End",
      "tab": "Tab",
      "arrowleft": "ArrowLeft",
      "left": "ArrowLeft",
      "arrowright": "ArrowRight",
      "right": "ArrowRight",
      "arrowup": "ArrowUp",
      "up": "ArrowUp",
      "arrowdown": "ArrowDown",
      "down": "ArrowDown",
      "super": "Meta",
      "space": "Space",
      "backspace": "Backspace",
    }
    return key_mapping.get(key, key)

  async def _press_key_combination(self, text: str):
    """Handle key combinations like ctrl+c, shift+a, etc."""
    if not self._page:
      raise ToolError("Page is not initialized")

    keys = [k.strip() for k in text.split("+")]
    keys = [self._map_key(k) for k in keys]

    # Press all modifier keys first
    for key in keys[:-1]:
      await self._page.keyboard.down(key)

    # Press and release the final key
    await self._page.keyboard.press(keys[-1])

    # Release modifier keys in reverse order
    for key in reversed(keys[:-1]):
      await self._page.keyboard.up(key)

  async def __call__(
    self,
    *,
    action: Action_20241022,
    text: str | None = None,
    coordinate: tuple[int, int] | None = None,
    **kwargs,
  ):
    if not self._page:
      raise ToolError("Page is not initialized")

    if action in ("mouse_move", "left_click_drag"):
      if coordinate is None:
        raise ToolError(f"coordinate is required for {action}")
      if text is not None:
        raise ToolError(f"text is not accepted for {action}")

      x, y = self.validate_and_get_coordinates(coordinate)

      if action == "mouse_move":
        await self._page.mouse.move(x, y)
      elif action == "left_click_drag":
        await self._page.mouse.move(x, y)
        await self._page.mouse.down()
        await self._page.mouse.up()

      return await self.screenshot()

    if action in ("key", "type"):
      if text is None:
        raise ToolError(f"text is required for {action}")
      if coordinate is not None:
        raise ToolError(f"coordinate is not accepted for {action}")
      if not isinstance(text, str):
        raise ToolError(output=f"{text} must be a string")

      if action == "key":
        if "+" in text:
          await self._press_key_combination(text)
        else:
          await self._page.keyboard.press(self._map_key(text))
      elif action == "type":
        await self._page.keyboard.type(text)

      return await self.screenshot()

    if action in (
      "left_click",
      "right_click",
      "double_click",
      "middle_click",
      "screenshot",
      "cursor_position",
    ):
      if text is not None:
        raise ToolError(f"text is not accepted for {action}")

      if action == "screenshot":
        return await self.screenshot()
      elif action == "cursor_position":
        # Get mouse position using JavaScript
        position = await self._page.evaluate("""() => {
          const e = document.elementFromPoint(window.innerWidth/2, window.innerHeight/2);
          const rect = e ? e.getBoundingClientRect() : null;
          return rect ? {x: rect.x, y: rect.y} : {x: 0, y: 0};
        }""")
        x, y = self.scale_coordinates(
          ScalingSource.COMPUTER,
          position["x"],
          position["y"]
        )
        return ToolResult(output=f"X={x},Y={y}")
      else:
        if coordinate is not None:
          x, y = self.validate_and_get_coordinates(coordinate)
          await self._page.mouse.move(x, y)

        button_mapping: Dict[str, Literal["left", "middle", "right"]] = {
          "left_click": "left",
          "right_click": "right",
          "middle_click": "middle",
          "double_click": "left",
        }
        button = button_mapping[action]

        if action == "double_click":
          await self._page.mouse.dblclick(x, y)
        else:
          await self._page.mouse.click(x, y, button=button)

        return await self.screenshot()

    raise ToolError(f"Invalid action: {action}")

class ComputerBrowserTool20241022(BaseComputerBrowserTool, BaseAnthropicTool):
  api_type: Literal["computer_20241022"] = "computer_20241022"

  def to_params(self) -> BetaToolComputerUse20241022Param:
    return {"name": self.name, "type": self.api_type, **self.options}

class ComputerBrowserTool20250124(BaseComputerBrowserTool, BaseAnthropicTool):
  api_type: Literal["computer_20250124"] = "computer_20250124"

  def to_params(self):
    return cast(
      BetaToolUnionParam,
      {"name": self.name, "type": self.api_type, **self.options},
    )

  async def __call__(
    self,
    *,
    action: Action_20250124,
    text: str | None = None,
    coordinate: tuple[int, int] | None = None,
    scroll_direction: ScrollDirection | None = None,
    scroll_amount: int | None = None,
    duration: int | float | None = None,
    key: str | None = None,
    **kwargs,
  ):
    if not self._page:
      raise ToolError("Page is not initialized")

    if action in ("left_mouse_down", "left_mouse_up"):
      if coordinate is not None:
        raise ToolError(f"coordinate is not accepted for {action=}.")
      if action == "left_mouse_down":
        await self._page.mouse.down()
      else:
        await self._page.mouse.up()
      return await self.screenshot()

    if action == "scroll":
      if scroll_direction is None or scroll_direction not in get_args(ScrollDirection):
        raise ToolError(f"{scroll_direction=} must be 'up', 'down', 'left', or 'right'")
      if not isinstance(scroll_amount, int) or scroll_amount < 0:
        raise ToolError(f"{scroll_amount=} must be a non-negative int")

      if coordinate is not None:
        x, y = self.validate_and_get_coordinates(coordinate)
        await self._page.mouse.move(x, y)

      scroll_x = 0
      scroll_y = 0
      amount = scroll_amount * 100  # Convert to pixels

      if scroll_direction == "up":
        scroll_y = -amount
      elif scroll_direction == "down":
        scroll_y = amount
      elif scroll_direction == "left":
        scroll_x = -amount
      else:  # right
        scroll_x = amount

      await self._page.mouse.wheel(scroll_x, scroll_y)
      return await self.screenshot()

    if action in ("hold_key", "wait"):
      if duration is None or not isinstance(duration, (int, float)):
        raise ToolError(f"{duration=} must be a number")
      if duration < 0:
        raise ToolError(f"{duration=} must be non-negative")
      if duration > 100:
        raise ToolError(f"{duration=} is too long.")

      if action == "hold_key":
        if text is None:
          raise ToolError(f"text is required for {action}")
        await self._page.keyboard.down(text)
        await asyncio.sleep(duration)
        await self._page.keyboard.up(text)
        return await self.screenshot()

      if action == "wait":
        await asyncio.sleep(duration)
        return await self.screenshot()

    if action == "triple_click":
      if coordinate is not None:
        x, y = self.validate_and_get_coordinates(coordinate)
        await self._page.mouse.move(x, y)
      await self._page.mouse.click(x, y, click_count=3)
      return await self.screenshot()

    return await super().__call__(
      action=action,
      text=text,
      coordinate=coordinate,
      key=key,
      **kwargs
    )
