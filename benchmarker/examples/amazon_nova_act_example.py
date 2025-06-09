from plato.sync_sdk import SyncPlato
from nova_act import NovaAct
import time
import os
import logging
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv
import requests


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_browser_ws_endpoint(cdp_port: int = 9222) -> str:
    """
    Gets the WebSocket endpoint URL for connecting to the Chrome DevTools Protocol.

    Args:
        cdp_port (int): The CDP debugging port (default: 9222)

    Returns:
        str: The WebSocket endpoint URL for CDP connection

    Makes a request to Chrome's debugging API to get the WebSocket URL.
    """
    response = requests.get(f"http://127.0.0.1:{cdp_port}/json/version")
    data = response.json()

    # extract the wsEndpoint from the response
    ws_endpoint = data["webSocketDebuggerUrl"]
    logger.info(f"Retrieved WebSocket endpoint: {ws_endpoint}")
    return ws_endpoint


def main():
    # Initialize the synchronous Plato client
    client = SyncPlato()

    try:
        # Create a new environment
        logger.info("Creating new environment...")
        env = client.make_environment(
            env_id="espocrm",  # Example environment ID
            viewport_width=1920,
            viewport_height=1080,
            interface_type=None,
        )
        env.wait_for_ready()

        # Use context manager to ensure proper cleanup
        logger.info(f"Environment created with ID: {env.id}")

        # Reset the environment with the task
        logger.info("Resetting environment with task...")
        env.reset()

        # Get the CDP URL for browser automation
        proxy_config = env.get_proxy_config()
        logger.info(f"Proxy config: {proxy_config}")

        # Create a new playwright browser with CDP Debugging address on port 9222
        logger.info("Creating Playwright browser with CDP debugging...")
        
        with sync_playwright() as p:
            # Launch browser with CDP debugging enabled and proxy configuration
            cdp_port = 9222
            browser = p.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=[
                    f"--remote-debugging-port={cdp_port}",
                    "--remote-debugging-address=0.0.0.0"
                ]
            )
            
            # Wait a moment for the browser to fully start
            time.sleep(2)
            
            # Get the proper WebSocket endpoint from the CDP API
            cdp_endpoint_url = get_browser_ws_endpoint(cdp_port)
            logger.info(f"CDP endpoint URL: {cdp_endpoint_url}")

            # navigate to http://espocrm.com and take a screenshot
            page = browser.new_page()
            page.goto("http://espocrm.com")
            page.screenshot(path="screenshot.png")
            page.close()

            # Wait a bit to see the environment in action
            with NovaAct(
                starting_page="http://espocrm.com",
                cdp_endpoint_url=cdp_endpoint_url,
            ) as nova:
                nova.act(
                    "Navigate to espocrm.com and login with the credentials admin/password.",
                )
            
            # Close the browser
            browser.close()

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Ensure the client session is closed
        env.close()
        client.close()


if __name__ == "__main__":
    main()
