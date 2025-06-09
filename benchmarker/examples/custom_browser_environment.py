from plato.sync_sdk import SyncPlato
from nova_act import NovaAct
import time
import os
import logging
import argparse
import uuid
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Amazon Nova Act Example with Extension Support")
    parser.add_argument("--extension-path", type=str, help="Path to local extension directory", default="/Users/pranavputta/Downloads/chrome-mv3-prod")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode", default=False)
    args = parser.parse_args()

    # Debug logging
    logger.info(f"Extension path argument: {args.extension_path}")
    logger.info(f"Extension path exists: {os.path.exists(args.extension_path) if args.extension_path else 'N/A'}")
    logger.info(f"Extension path is directory: {os.path.isdir(args.extension_path) if args.extension_path else 'N/A'}")
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

        # Get the CDP URL for browser automation
        proxy_config = env.get_proxy_config()
        logger.info(f"Proxy config: {proxy_config}")

        # Create a new playwright browser with CDP Debugging address on port 9222
        logger.info("Creating Playwright browser with CDP debugging...")
        
        with sync_playwright() as p:
            # Launch browser with CDP debugging enabled and proxy configuration
            cdp_port = 9222
            
            # Prepare browser launch arguments
            browser_args = [
                f"--remote-debugging-port={cdp_port}",
                "--remote-debugging-address=127.0.0.1"
            ]
            
            # Add extension loading if extension path is provided
            if args.extension_path:
                logger.info(f"Extension path provided: {args.extension_path}")
                if os.path.exists(args.extension_path) and os.path.isdir(args.extension_path):
                    logger.info(f"Loading extension from: {args.extension_path}")
                    browser_args.append(f"--load-extension={args.extension_path}")
                    browser_args.append(f"--disable-extensions-except={args.extension_path}")
                    browser_args.append("--disable-http2")
                    
                    logger.info(f"Browser args with extension: {browser_args}")
                    
                    # Have to use persistent context for extensions
                    browser = p.chromium.launch_persistent_context(
                        args=browser_args,
                        headless=args.headless,
                        user_data_dir=f"/tmp/user_data_{uuid.uuid4()}",
                        proxy=proxy_config,
                    )
                    logger.info("Browser launched with persistent context and extension")
                else:
                    logger.error(f"Extension path does not exist or is not a directory: {args.extension_path}")
                    return
            else:
                logger.info("No extension path provided, launching regular browser")
                browser = p.chromium.launch(
                    headless=args.headless,
                    proxy=proxy_config,
                    args=browser_args
                )
            
            # Wait a moment for the browser to fully start
            time.sleep(2)
            
            # Get the proper WebSocket endpoint from the CDP API
            cdp_endpoint_url = get_browser_ws_endpoint(cdp_port)
            logger.info(f"CDP endpoint URL: {cdp_endpoint_url}")

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

