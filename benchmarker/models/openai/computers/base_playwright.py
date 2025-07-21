import asyncio
import base64
from typing import List, Dict, Literal, Optional
# Import async versions and PlaywrightContextManager from internal module
from playwright.async_api import (
    async_playwright,
    Browser as AsyncBrowser,
    Page as AsyncPage,
    Playwright,
    Response
)
from playwright.async_api._context_manager import PlaywrightContextManager
from models.openai.computers.computer import Computer

# Optional: key mapping if your model uses "CUA" style keys
CUA_KEY_TO_PLAYWRIGHT_KEY = {
    "/": "Divide",
    "\\": "Backslash",
    "alt": "Alt",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "arrowup": "ArrowUp",
    "backspace": "Backspace",
    "capslock": "CapsLock",
    "cmd": "Meta",
    "ctrl": "Control",
    "delete": "Delete",
    "end": "End",
    "enter": "Enter",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "option": "Alt",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "shift": "Shift",
    "space": " ",
    "super": "Meta",
    "tab": "Tab",
    "win": "Meta",
}


class BasePlaywrightComputer(Computer):
    """
    Abstract base for async Playwright-based computers:

      - Subclasses override `_get_browser_and_page()` to do local or remote connection,
        returning (AsyncBrowser, AsyncPage).
      - This base class handles context creation (`__aenter__`/`__aexit__`),
        plus standard "Computer" actions like click, scroll, etc.
      - We also have extra browser actions: `goto(url)` and `back()`.
    """

    environment: Literal["browser"] = "browser"
    @property
    def dimensions(self) -> tuple[int, int]:
        return (1920, 1080)


    def __init__(self):
        # Correct type hint for the context manager
        self._playwright_manager: Optional[PlaywrightContextManager] = None
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[AsyncBrowser] = None
        self._page: Optional[AsyncPage] = None

    async def __aenter__(self):
        # Start Playwright using the context manager correctly
        self._playwright_manager = async_playwright()
        # Enter the context manager to get the Playwright instance
        self._playwright = await self._playwright_manager.__aenter__()

        if not self._playwright:
             raise RuntimeError("Failed to start Playwright")

        # Pass the non-optional Playwright instance
        self._browser, self._page = await self._get_browser_and_page(self._playwright)

        if not self._page:
             raise RuntimeError("Failed to get a page from _get_browser_and_page")

        # async def handle_route(route: Route, request: Request):
        #     url = request.url
        #     if check_blocklisted_url(url):
        #         print(f"Flagging blocked domain: {url}")
        #         try:
        #             await route.abort()
        #         except Exception as e:
        #             print(f"Error aborting route for {url}: {e}")
        #     else:
        #         try:
        #             await route.continue_()
        #         except Exception as e:
        #             print(f"Error continuing route for {url}: {e}")

        # await self._page.route("**/*", handle_route)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                print(f"Error closing browser: {e}")
        # Exit the playwright context manager
        if self._playwright_manager:
            try:
                await self._playwright_manager.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                print(f"Error stopping playwright: {e}")
        self._browser = None
        self._page = None
        self._playwright = None
        self._playwright_manager = None

    # Make sync again - accessing page.url is not async
    def get_current_url(self) -> str:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        return self._page.url

    # --- Common "Computer" actions ---
    async def screenshot(self) -> str:
        """Capture only the viewport (not full_page)."""
        if not self._page:
             raise RuntimeError("Page is not initialized")
        png_bytes = await self._page.screenshot(full_page=False)
        return base64.b64encode(png_bytes).decode("utf-8")

    async def click(self, x: int, y: int, button: str = "left") -> None:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        button_mapping: Dict[str, Literal['left', 'middle', 'right']] = {
            "left": "left",
            "right": "right",
            "middle": "middle",
        }
        playwright_button = button_mapping.get(button.lower(), "left")

        match playwright_button:
            case "left" | "right" | "middle":
                await self._page.mouse.click(x, y, button=playwright_button)

    async def double_click(self, x: int, y: int) -> None:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        await self._page.mouse.dblclick(x, y)

    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        await self._page.mouse.move(x, y)
        await self._page.mouse.wheel(scroll_x, scroll_y)

    async def type(self, text: str) -> None:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        await self._page.keyboard.type(text)

    async def wait(self, ms: int = 1000) -> None:
        await asyncio.sleep(ms / 1000)

    async def move(self, x: int, y: int) -> None:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        await self._page.mouse.move(x, y)

    async def keypress(self, keys: List[str]) -> None:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        mapped_keys = [CUA_KEY_TO_PLAYWRIGHT_KEY.get(key.lower(), key) for key in keys]
        for key in mapped_keys:
            await self._page.keyboard.down(key)
        for key in reversed(mapped_keys):
            await self._page.keyboard.up(key)

    async def drag(self, path: List[Dict[str, int]]) -> None:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        if not path:
            return
        await self._page.mouse.move(path[0]["x"], path[0]["y"])
        await self._page.mouse.down()
        for point in path[1:]:
            await self._page.mouse.move(point["x"], point["y"])
        await self._page.mouse.up()

    # --- Extra browser-oriented actions ---
    async def goto(self, url: str) -> Optional[Response]:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        try:
            response = await self._page.goto(url)
            return response
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return None

    async def back(self) -> Optional[Response]:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        try:
            response = await self._page.go_back()
            return response
        except Exception as e:
            print(f"Error going back: {e}")
            return None

    async def forward(self) -> Optional[Response]:
        if not self._page:
             raise RuntimeError("Page is not initialized")
        try:
            response = await self._page.go_forward()
            return response
        except Exception as e:
            print(f"Error going forward: {e}")
            return None

    # --- Subclass hook ---
    async def _get_browser_and_page(self, playwright: Playwright) -> tuple[AsyncBrowser, AsyncPage]:
        """Subclasses must implement, returning (AsyncBrowser, AsyncPage)."""
        raise NotImplementedError
