import asyncio
from playwright.async_api import async_playwright

from plato.models import PlatoTask
from plato.sdk import Plato

async def test_environment_lifecycle():
    """Test the lifecycle of a Plato environment including creation, reset, and closure."""
    # Initialize the client
    # client = Plato(base_url="https://plato.so/api")
    # client = Plato(base_url="https://staging.plato.so/api")
    client = Plato(base_url="http://54.219.139.8:25565/api")
    task = PlatoTask(
        name="example_task",
        prompt="",
        start_url="https://www.doordash.com/"
    )

    # Create and initialize the environment
    env = await client.make_environment("doordash")

    try:
        # Wait for the environment to be ready
        print("Waiting for environment to be ready")
        await env.wait_for_ready(timeout=30.0)
        print("Environment ready")
        await env.reset()
        print("Environment reset")

        # Get the CDP URL for browser connection
        print("Getting CDP URL")
        cdp_url = await env.get_cdp_url()
        print(f"Environment ready with CDP URL: {cdp_url}")

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            print("Connected to browser")
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.doordash.com/")
            print("Navigating to Doordash")
            await page.wait_for_timeout(3000)
            print("Waited for 3 seconds")
            await page.screenshot(path="screenshot.png")
            print("Screenshot taken")
            await asyncio.sleep(180)

    finally:
        # Always ensure we close the environment
        await env.close()
        print("Environment closed")
        # Close the client to cleanup aiohttp session
        await client.close()
        print("Client closed")

async def test_multiple_contexts():
    """Test creating multiple browser contexts in a single Plato environment."""
    client = Plato(base_url="https://staging.plato.so/api")
    task = PlatoTask(
        name="multi_context_test",
        metadata={"type": "test"},
        initial_state={"url": "https://example.com"}
    )

    env = await client.make_environment("doordash")

    try:
        print("Waiting for environment to be ready")
        await env.wait_for_ready(timeout=30.0)
        print("Environment ready")
        await env.reset()
        print("Environment reset")

        print("Getting CDP URL")
        cdp_url = await env.get_cdp_url()
        print(f"Environment ready with CDP URL: {cdp_url}")

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            print("Connected to browser")
            
            # Create three different contexts and take screenshots in parallel
            async def handle_context(i: int):
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto("https://www.doordash.com/")
                print(f"Navigating to Doordash in context {i+1}")
                await page.wait_for_timeout(3000)
                print(f"Taking screenshot for context {i+1}")
                await page.screenshot(path=f"screenshot_context_{i+1}.png")
                await context.close()
                print(f"Context {i+1} closed")

            tasks = [handle_context(i) for i in range(2)]
            await asyncio.gather(*tasks)

    finally:
        await env.close()
        print("Environment closed")
        await client.close()
        print("Client closed")

if __name__ == "__main__":
    asyncio.run(test_environment_lifecycle())
    # Uncomment to run the multiple contexts test
    # asyncio.run(test_multiple_contexts())
