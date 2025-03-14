import asyncio
from playwright.async_api import async_playwright

from plato.models import PlatoTask
from plato.sdk import Plato

async def test_environment_lifecycle():
    """Test the lifecycle of a Plato environment including creation, reset, and closure."""
    # Initialize the client
    client = PlatoClient(base_url="https://staging.plato.so/api")
    # Create a sample task
    task = PlatoTask(
        name="example_task",
        metadata={"type": "test"},
        initial_state={"url": "https://example.com"}
    )

    # Create and initialize the environment
    env = await client.make_environment("doordash")

    try:
        # Wait for the environment to be ready
        print("Waiting for environment to be ready")
        await env.wait_for_ready(timeout=30.0)
        await env.reset()

        # Get the CDP URL for browser connection
        cdp_url = await env.get_cdp_url()
        print(f"Environment ready with CDP URL: {cdp_url}")

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            page = browser.contexts[0].pages[0]
            print("Connected to browser")
            await page.goto("https://www.doordash.com/")
            print("Navigating to Doordash")
            await page.wait_for_timeout(3000)
            print("Waited for 3 seconds")
            await page.screenshot(path="screenshot.png")
            print("Screenshot taken")

    finally:
        # Always ensure we close the environment
        await env.close()
        print("Environment closed")
        # Close the client to cleanup aiohttp session
        await client.close()
        print("Client closed")

if __name__ == "__main__":
    asyncio.run(test_environment_lifecycle())
