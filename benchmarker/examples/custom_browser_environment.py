from plato.sync_sdk import SyncPlato
from nova_act import NovaAct
import time
import os
import logging
import argparse
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Amazon Nova Act Example")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode", default=False)
    args = parser.parse_args()

    logger.info(f"Headless mode: {args.headless}")

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

        # Get the proxy configuration
        proxy_config = env.get_proxy_config()
        logger.info(f"Proxy config: {proxy_config}")

        # Create a new playwright browser
        logger.info("Creating Playwright browser...")
        
        with sync_playwright() as p:
            # Launch browser with proxy configuration
            browser = p.chromium.launch(
                headless=args.headless,
                proxy=proxy_config,
            )
            
            page = browser.new_page()
            page.goto("http://espocrm.com")
            time.sleep(2)
            page.screenshot(path="screenshot.png")
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

