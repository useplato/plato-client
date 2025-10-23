import asyncio
import base64
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Awaitable, Optional, Literal

from ..openai.computers.remote_playwright import RemotePlaywrightComputer


@dataclass
class EnvState:
    """Snapshot returned to the Gemini agent after each operation."""

    screenshot: bytes
    url: str


class GeminiComputerBridge:
    """Wraps the async RemotePlaywrightComputer with the sync interface expected by the Gemini agent."""

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        computer: RemotePlaywrightComputer,
        action_callback: Optional[Callable[[dict[str, Any]], Awaitable[None] | None]] = None,
        search_engine_url: str = "https://www.google.com",
        wait_after_action: float = 0.5,
    ):
        self._loop = loop
        self._computer = computer
        self._action_callback = action_callback
        self._search_engine_url = search_engine_url
        self._wait_after_action = wait_after_action
        self._screen_size: tuple[int, int] | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def screen_size(self) -> tuple[int, int]:
        if self._screen_size is None:
            return self._refresh_screen_size()
        return self._screen_size

    def _denormalize_scalar(self, value: int | float, axis: Literal["x", "y"]) -> int:
        width, height = self.screen_size
        size = width if axis == "x" else height
        normalized = max(0.0, min(float(value), 1000.0))
        pixel_value = int(round(normalized / 1000.0 * size))
        # Keep coordinates inside the viewport
        return max(0, min(size - 1, pixel_value))

    def _denormalize_point(self, x: int | float, y: int | float) -> tuple[int, int]:
        return self._denormalize_scalar(x, "x"), self._denormalize_scalar(y, "y")

    def _denormalize_magnitude(self, magnitude: int | float, axis: Literal["x", "y"]) -> int:
        width, height = self.screen_size
        size = width if axis == "x" else height
        normalized = max(0.0, min(float(magnitude), 1000.0))
        pixels = int(round(normalized / 1000.0 * size))
        return max(0, pixels)

    def _run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def _refresh_screen_size(self) -> tuple[int, int]:
        try:
            width, height = self._run(self._computer.viewport_size())
        except Exception:
            width, height = self._computer.dimensions
        if width <= 0 or height <= 0:
            width, height = self._computer.dimensions
        self._screen_size = (width, height)
        return self._screen_size

    def _dispatch_callback(self, payload: dict[str, Any]) -> None:
        if not self._action_callback:
            return
        result = self._action_callback(payload)
        if inspect.iscoroutine(result):
            cb_future = asyncio.run_coroutine_threadsafe(result, self._loop)
            cb_future.result()

    def _wait_briefly(self) -> None:
        if self._wait_after_action <= 0:
            return
        self._run(self._computer.wait(int(self._wait_after_action * 1000)))

    def _capture_env_state(self) -> tuple[EnvState, str | None]:
        self._refresh_screen_size()
        screenshot_b64 = self._run(self._computer.screenshot())
        screenshot_bytes = base64.b64decode(screenshot_b64) if screenshot_b64 else b""
        url = self._computer.get_current_url()
        return EnvState(screenshot=screenshot_bytes, url=url), screenshot_b64

    def _notify_action(self, action: str, params: dict[str, Any]) -> None:
        payload: dict[str, Any] = {"type": "action", "action": action, "params": params}
        payload["result"] = {"has_image": True}
        self._dispatch_callback(payload)

    def _run_with_state(self, action: str, params: dict[str, Any], coro) -> EnvState:
        self._run(coro)
        self._wait_briefly()
        state, _ = self._capture_env_state()
        self._notify_action(action, params)
        return state

    def current_state(self) -> EnvState:
        state, _ = self._capture_env_state()
        self._notify_action("current_state", {})
        return state

    # ------------------------------------------------------------------
    # Gemini computer-use API surface
    # ------------------------------------------------------------------
    def open_web_browser(self) -> EnvState:
        state, _ = self._capture_env_state()
        self._notify_action("open_web_browser", {})
        return state

    def click_at(self, x: int, y: int) -> EnvState:
        px, py = self._denormalize_point(x, y)
        params = {"x": x, "y": y, "pixel_x": px, "pixel_y": py}
        return self._run_with_state("click_at", params, self._computer.click(px, py, button="left"))

    def hover_at(self, x: int, y: int) -> EnvState:
        px, py = self._denormalize_point(x, y)
        params = {"x": x, "y": y, "pixel_x": px, "pixel_y": py}
        return self._run_with_state("hover_at", params, self._computer.move(px, py))

    def type_text_at(
        self,
        x: int,
        y: int,
        text: str,
        press_enter: bool = False,
        clear_before_typing: bool = True,
    ) -> EnvState:
        params = {
            "x": x,
            "y": y,
            "text": text,
            "press_enter": press_enter,
            "clear_before_typing": clear_before_typing,
        }
        px, py = self._denormalize_point(x, y)
        self._run(self._computer.click(px, py, button="left"))
        self._wait_briefly()

        if clear_before_typing:
            self._run(self._computer.keypress(["Control", "A"]))
            self._run(self._computer.keypress(["Delete"]))

        self._run(self._computer.type(text))

        if press_enter:
            self._run(self._computer.keypress(["Enter"]))

        self._wait_briefly()
        state, _ = self._capture_env_state()
        params.update({"pixel_x": px, "pixel_y": py})
        self._notify_action("type_text_at", params)
        return state

    def scroll_document(self, direction: Literal["up", "down", "left", "right"], magnitude: int = 500) -> EnvState:
        params = {"direction": direction, "magnitude": magnitude}
        width, height = self.screen_size
        center_x = width // 2
        center_y = height // 2

        if direction == "up":
            scroll_amount = self._denormalize_magnitude(magnitude, "y")
            self._run(self._computer.scroll(center_x, center_y, 0, -scroll_amount))
        elif direction == "down":
            scroll_amount = self._denormalize_magnitude(magnitude, "y")
            self._run(self._computer.scroll(center_x, center_y, 0, scroll_amount))
        elif direction == "left":
            scroll_amount = self._denormalize_magnitude(magnitude, "x")
            self._run(self._computer.scroll(center_x, center_y, -scroll_amount, 0))
        elif direction == "right":
            scroll_amount = self._denormalize_magnitude(magnitude, "x")
            self._run(self._computer.scroll(center_x, center_y, scroll_amount, 0))
        else:
            raise ValueError(f"Unsupported scroll direction: {direction}")

        self._wait_briefly()
        state, _ = self._capture_env_state()
        self._notify_action("scroll_document", params)
        return state

    def scroll_at(
        self,
        x: int,
        y: int,
        direction: Literal["up", "down", "left", "right"],
        magnitude: int,
    ) -> EnvState:
        px, py = self._denormalize_point(x, y)
        params = {
            "x": x,
            "y": y,
            "direction": direction,
            "magnitude": magnitude,
            "pixel_x": px,
            "pixel_y": py,
        }
        dx = dy = 0
        if direction == "up":
            dy = -self._denormalize_magnitude(magnitude, "y")
        elif direction == "down":
            dy = self._denormalize_magnitude(magnitude, "y")
        elif direction == "left":
            dx = -self._denormalize_magnitude(magnitude, "x")
        elif direction == "right":
            dx = self._denormalize_magnitude(magnitude, "x")
        else:
            raise ValueError(f"Unsupported scroll direction: {direction}")

        params["pixel_magnitude"] = abs(dx or dy)
        return self._run_with_state("scroll_at", params, self._computer.scroll(px, py, dx, dy))

    def wait_5_seconds(self) -> EnvState:
        state = self._run_with_state("wait_5_seconds", {"duration_ms": 5000}, self._computer.wait(5000))
        return state

    def go_back(self) -> EnvState:
        return self._run_with_state("go_back", {}, self._computer.back())

    def go_forward(self) -> EnvState:
        return self._run_with_state("go_forward", {}, self._computer.forward())

    def search(self) -> EnvState:
        return self._run_with_state("search", {"url": self._search_engine_url}, self._computer.goto(self._search_engine_url))

    def navigate(self, url: str) -> EnvState:
        normalized = url if url.startswith(("http://", "https://")) else f"https://{url}"
        return self._run_with_state("navigate", {"url": normalized}, self._computer.goto(normalized))

    def key_combination(self, keys: list[str]) -> EnvState:
        return self._run_with_state("key_combination", {"keys": keys}, self._computer.keypress(keys))

    def drag_and_drop(self, x: int, y: int, destination_x: int, destination_y: int) -> EnvState:
        start_px, start_py = self._denormalize_point(x, y)
        end_px, end_py = self._denormalize_point(destination_x, destination_y)
        path = [{"x": start_px, "y": start_py}, {"x": end_px, "y": end_py}]
        params = {
            "x": x,
            "y": y,
            "destination_x": destination_x,
            "destination_y": destination_y,
            "start_pixel_x": start_px,
            "start_pixel_y": start_py,
            "dest_pixel_x": end_px,
            "dest_pixel_y": end_py,
        }
        return self._run_with_state("drag_and_drop", params, self._computer.drag(path))
