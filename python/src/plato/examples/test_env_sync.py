import time

from plato.sync_sdk import SyncPlato

from dotenv import load_dotenv

load_dotenv('.env')


def test_environment_lifecycle():
    """Test the lifecycle of a Plato environment including creation, reset, and closure."""
    # Initialize the client
    client = SyncPlato(base_url="https://plato.so/api", api_key="6d7dd81c-ad14-428c-87ac-d8c1f05c9a7d")
    # client = Plato(base_url="https://staging.plato.so/api")
    # client = Plato(base_url="http://54.219.32.250:8080/api")
    # Create and initialize the environment
    # env = client.make_environment("espocrm")
    env = client.make_environment('cosmopolitan_lasvegas', interface_type=None, keepalive=True)

    try:
        print(env.id)
        # Wait for the environment to be ready
        print("Waiting for environment to be ready")
        env.wait_for_ready()

        print("Environment ready")
        start_time = time.time()
        # tasks = client.load_tasks("cosmopolitan_lasvegas")
        # task = tasks[0]
        # print(f"Task: {task}")
        env.reset()
        print("Environment reset")
        end_time = time.time()
        print(f"Time taken to reset environment: {end_time - start_time} seconds")

        breakpoint()

        # Get the CDP URL for browser connection
        # print("Getting CDP URL")
        # cdp_url = env.get_cdp_url()
        # print(f"Environment ready with CDP URL: {cdp_url}")

        # live_url = client.get_live_view_url(env.id)
        # print(f"Live view URL: {live_url}")

        state = env.get_state()
        print(f"State: {state}")

        # with sync_playwright() as p:
        #     browser = p.chromium.connect_over_cdp(cdp_url)
        #     print("Connected to browser")
        #     context = browser.new_context()
        #     page = context.new_page()
        #     breakpoint()
        #     time.sleep(10000)
        #     page.goto("https://www.doordash.com/")
        #     print("Navigating to Doordash")
        #     page.wait_for_timeout(3000)
        #     print("Waited for 3 seconds")
        #     page.screenshot(path="screenshot.png")
        #     print("Screenshot taken")
        #     # get the state
        #     state = env.get_state()
        #     print(f"State: {state}")
        #     result = env.evaluate()
        #     print(f"Evaluation result: {result}")
        #     # time.sleep(180)

    finally:
        # Always ensure we close the environment
        env.close()
        print("Environment closed")
        # Close the client to cleanup session
        client.close()
        print("Client closed")


if __name__ == "__main__":
    test_environment_lifecycle()
    # Uncomment to run the multiple contexts test
    # test_multiple_contexts()
