
from plato.sync_sdk import SyncPlato
import logging
import argparse
from plato.sync_env import SyncPlatoEnvironment
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_environment(env_id: str = "doordash", keepalive: bool = False) -> str:
    """
    Create a new environment and return its job ID.

    Args:
        env_id: The ID of the environment to create
        keepalive: Whether to keep the environment alive

    Returns:
        The job ID of the created environment
    """
    logger.info(f"Creating new environment with ID: {env_id}")

    # Initialize the synchronous Plato client
    client = SyncPlato()

    try:
        # Create a new environment
        env = client.make_environment(
            env_id=env_id,
            interface_type=None,  # Set interface type to None so you can run on your own browser
            keepalive=keepalive,
        )
        env.wait_for_ready()

        job_id = env.id
        logger.info(f"Environment created with job ID: {job_id}")

        # Close the client but keep the environment alive if keepalive is True
        client.close()

        return job_id

    except Exception as e:
        logger.error(f"An error occurred while creating environment: {e}")
        client.close()
        raise


def reuse_environment(job_id: str, headless: bool = False) -> None:
    """
    Reuse an existing environment with the given job ID.

    Args:
        job_id: The job ID of the environment to reuse
        headless: Whether to run the browser in headless mode
    """
    logger.info(f"Reusing environment with job ID: {job_id}")

    # Initialize the synchronous Plato client
    client = SyncPlato()

    try:
        # Create environment from existing job ID
        env = SyncPlatoEnvironment.from_id(client, job_id)
        logger.info(f"Successfully loaded environment with ID: {env.id}")

        # Reset the environment
        logger.info("Resetting environment...")
        env.reset()
        logger.info("Environment reset successful")

        # Get the public URL for browser navigation
        public_url = env.get_public_url()
        logger.info(f"Public URL: {public_url}")

        # Create a new playwright browser
        logger.info("Creating Playwright browser...")

        with sync_playwright() as p:
            # Launch browser normally (no proxy needed for public URL)
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--ignore-certificate-errors",
                    "--ignore-ssl-errors",
                    "--disable-http2",
                ],
            )

            page = browser.new_page()
            logger.info("Successfully created browser page")

            # Navigate to the public URL
            logger.info(f"Navigating to public URL: {public_url}")
            page.goto(public_url)
            logger.info("Successfully navigated to public URL")

            # Close the browser
            browser.close()
            logger.info("Browser closed successfully")

    except Exception as e:
        logger.error(f"An error occurred while reusing environment: {e}")
        raise
    finally:
        # Ensure the client session is closed
        client.close()


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test environment reuse functionality")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
        default=False,
    )
    parser.add_argument(
        "--env-id",
        type=str,
        help="The ID of the environment to create",
        default="doordash",
    )
    parser.add_argument(
        "--keepalive",
        action="store_true",
        help="Keep the environment alive",
        default=False,
    )
    parser.add_argument(
        "--existing-job-id",
        type=str,
        help="The ID of an existing job to use",
        default=None,
    )
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Only create an environment and return the job ID",
        default=False,
    )
    args = parser.parse_args()

    logger.info(f"Headless mode: {args.headless}")

    try:
        if args.create_only:
            # Only create environment and return job ID
            job_id = create_environment(args.env_id, args.keepalive)
            print("\n=== Environment created successfully ===")
            print(f"Job ID: {job_id}")
            print(f"Use this job ID with --existing-job-id {job_id} to reuse the environment")

        elif args.existing_job_id:
            # Reuse existing environment
            reuse_environment(args.existing_job_id, args.headless)
            print("\n=== Environment reused successfully ===")
            print(f"Job ID: {args.existing_job_id}")

        else:
            # Create environment first, then reuse it
            print("=== Step 1: Creating environment ===")
            job_id = create_environment(args.env_id, args.keepalive)

            print("\n=== Step 2: Reusing environment ===")
            reuse_environment(job_id, args.headless)

            print("\n=== Test completed successfully ===")
            print(f"Job ID: {job_id}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
