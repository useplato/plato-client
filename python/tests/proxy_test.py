import logging
import os
from plato.sdk import Plato
from dotenv import load_dotenv
from playwright.async_api import async_playwright
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
load_dotenv()
BASE_URL = os.getenv("PLATO_BASE_URL")
API_KEY = os.getenv("PLATO_API_KEY")
async def main():
    client = Plato(base_url=BASE_URL, api_key=API_KEY)
    running_sessions_count = await client.get_running_sessions_count()
    env = await client.make_environment(
        "doordash",
        fast=True,
        interface_type=None,
        # tag="prod-latest"
    )
    await env.wait_for_ready()
    await env.reset()
    public_url = await env.get_public_url()
    # proxy_url = "https://proxy.plato.so:9000"
    proxy_config = await env.get_proxy_config()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,  # Set to True for headless mode
            proxy={
                "server": proxy_config["server"],
                "username": proxy_config["username"],
                "password": proxy_config["password"],
            },
            args=[
                "--ignore-certificate-errors",
                "--ignore-ssl-errors",
                "--disable-http2",
            ],
        )
        page = await browser.new_page()
        try:
            print(f"Successfully loaded: {page.url}")
            print(f"Page title: {await page.title()}")
            # Keep the browser open for a bit to see the result
            await asyncio.sleep(1000)
        except Exception as e:
            print(f"Error navigating to website: {e}")
        await browser.close()
    print(public_url)
    input("Press Enter to continue...")
    # tasks = await client.load_tasks("firefly")
    # task = tasks[0]
    # await env.reset(task=task)
    # breakpoint()
    # state = await env.get_state()
    await env.close()
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
