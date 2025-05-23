from plato.sync_sdk import SyncPlato
from nova_act import NovaAct
import time
import os
import logging
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Initialize the synchronous Plato client
    client = SyncPlato()

    try:
        # Create a new environment
        logger.info("Creating new environment...")
        env = client.make_environment(
            env_id="espocrm",  # Example environment ID
            open_page_on_start=True,
            viewport_width=1920,
            viewport_height=1080,
        )
        env.wait_for_ready()

        # Use context manager to ensure proper cleanup
        logger.info(f"Environment created with ID: {env.id}")

        # Reset the environment with the task
        logger.info("Resetting environment with task...")
        env.reset()

        # Get the CDP URL for browser automation
        cdp_url = env.get_cdp_url()
        logger.info(f"CDP URL: {cdp_url}")

        live_view_url = env.get_live_view_url()
        logger.info(f"Live view URL: {live_view_url}")

        # Wait a bit to see the environment in action
        with NovaAct(
            starting_page="http://espocrm.com", cdp_endpoint_url=cdp_url
        ) as nova:
            nova.act(
                "Navigate to espocrm.com and login with the credentials admin/password.",
            )

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Ensure the client session is closed
        env.close()
        client.close()


if __name__ == "__main__":
    main()
