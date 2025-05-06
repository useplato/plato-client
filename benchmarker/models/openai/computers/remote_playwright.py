from playwright.async_api import Browser as AsyncBrowser, Page as AsyncPage, Playwright
from .base_playwright import BasePlaywrightComputer
from typing import Optional # Import Optional
import logging

logger = logging.getLogger(__name__)

class RemotePlaywrightComputer(BasePlaywrightComputer):
    """Connects to an existing Chromium instance over CDP using async Playwright."""

    def __init__(self, cdp_url: str):
        # Assuming BasePlaywrightComputer.__init__ is compatible or also made async
        super().__init__()
        self.cdp_url = cdp_url
        # Explicitly type hint the attributes to use Async types
        self._browser: Optional[AsyncBrowser] = None
        self._page: Optional[AsyncPage] = None
        # Playwright instance is typically managed in the base class's __aenter__

    async def _get_browser_and_page(self, playwright: Playwright) -> tuple[AsyncBrowser, AsyncPage]:
        width, height = self.dimensions
        # Use the playwright instance passed from the (assumed) async base class __aenter__
        browser = await playwright.chromium.connect_over_cdp(self.cdp_url)
        logger.info(f"Connected to browser: {browser}")

        # Always create a new context
        context = await browser.new_context(viewport={"width": width, "height": height})
        logger.info(f"Created new context: with dimensions {width}x{height}")
        # Add event listeners for page creation and closure
        context.on("page", self._handle_new_page) # Keep handlers sync for simplicity unless they need await

        # Find an existing page or create a new one
        if context.pages:
            page = context.pages[0] # Use the first page found
            await page.set_viewport_size({"width": width, "height": height})
        else:
            page = await context.new_page()
            # Viewport is set by context, but explicit set_viewport_size might still be needed
            # depending on exact behavior desired.
            await page.set_viewport_size({"width": width, "height": height})

        page.on("close", self._handle_page_close) # Keep handlers sync

        # Optional: Navigate to a default page if needed, or ensure a page is active
        # await page.goto("about:blank") # Example: Ensure a blank page

        # Store browser and page if the base class expects it
        self._browser = browser
        self._page = page

        return browser, page

    # Event handlers can remain synchronous if they don't perform async operations
    # If they need to await, they should be async def and the .on() registration handles it.
    def _handle_new_page(self, page: AsyncPage):
        """Handle the creation of a new page."""
        # This might need to become async if complex logic/await is needed
        print(f"New page created: {page.url}")
        # Be careful with directly assigning self._page here in async context,
        # consider thread-safety or locking if multiple events can occur concurrently.
        # Simple assignment might be okay depending on usage pattern.
        self._page = page
        page.on("close", self._handle_page_close)

    def _handle_page_close(self, page: AsyncPage):
        """Handle the closure of a page."""
        # This might need to become async if complex logic/await is needed
        print(f"Page closed: {page.url}")
        if self._page == page:
            if self._browser and self._browser.contexts and self._browser.contexts[0].pages:
                self._page = self._browser.contexts[0].pages[-1]
                print(f"Switched active page to: {self._page.url}")
            else:
                print("Warning: All pages have been closed.")
                self._page = None

    # Ensure __aenter__ and __aexit__ are correctly implemented, likely in the base class
    # Example sketch (if needed here, but likely belongs in BasePlaywrightComputer):
    # async def __aenter__(self):
    #   self._playwright_manager = async_playwright()
    #   self._playwright = await self._playwright_manager.__aenter__()
    #   self._browser, self._page = await self._get_browser_and_page(self._playwright)
    #   return self

    # async def __aexit__(self, exc_type, exc_val, exc_tb):
    #   if self._browser:
    #       await self._browser.close() # Or just context.close() if appropriate
    #   if self._playwright_manager:
    #       await self._playwright_manager.__aexit__(exc_type, exc_val, exc_tb)
