import asyncio
import os

from playwright.async_api import async_playwright
from plato.sdk import Plato

from dotenv import load_dotenv

load_dotenv(".env")


async def test_google_passthrough():
    """Test creating a backup of an EspoCRM environment."""

    try:
        # Initialize the client
        client = Plato(base_url=os.getenv("PLATO_API_URL", "https://plato.so/api"))

        # Create and initialize the EspoCRM environment
        env = await client.make_environment(
            "opentable",
            env_config={
                "passthrough_all_ood_requests": True,
                "replay_session_ids": [],
            },
            record_network_requests=True,
        )
        print(f"Environment ID: {env.id}")

        try:
            # Wait for the environment to be ready
            print("Waiting for environment to be ready...")
            await env.wait_for_ready(timeout=300.0)
            print("Environment ready")

            # Reset the environment
            await env.reset()
            print("Environment reset")

            # Get the CDP URL for browser connection
            print("Getting CDP URL...")
            cdp_url = await env.get_cdp_url()

            # Get live view URL
            live_url = await client.get_live_view_url(env.id)
            print(f"Live view URL: {live_url}")

            # Connect to browser and perform some basic actions
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                context = browser.contexts[0]
                page = context.pages[0]
                print("Connected to browser")

                await page.goto("https://www.opentable.com/")
                breakpoint()

        finally:
            # Always ensure we close the environment
            await env.close()
            print("Environment closed")

            # Close the client to cleanup aiohttp session
            await client.close()
            print("Client closed")

    except Exception as e:
        print(f"Test failed with error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("GOOGLE PASSTHROUGH TEST")
    print("=" * 60)

    # Run single backup test
    asyncio.run(test_google_passthrough())
