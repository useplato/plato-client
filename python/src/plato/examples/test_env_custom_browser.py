import time
from playwright.sync_api import sync_playwright, ProxySettings
from plato.sync_sdk import SyncPlato
from dotenv import load_dotenv

load_dotenv('.env')


def test_custom_browser_environment():
    """Test custom browser control with Plato environment."""
    # Initialize the synchronous client
    api_key = "5cdd615f-612a-4a5a-bbe0-d0a52fff831d"
    client = SyncPlato(api_key=api_key, base_url="http://localhost:8080/api")

    # Create environment with interface_type=None for custom browser control
    env = client.make_environment(
        env_id="cosmopolitan_lasvegas",
        interface_type=None  # Required for custom browser
    )

    try:
        print(f"Environment ID: {env.id}")
        print("Waiting for environment to be ready")
        env.wait_for_ready()
        print("Environment ready")

        # Load tasks and reset environment
        tasks = client.load_tasks("cosmopolitan_lasvegas")
        if len(tasks):
          env.reset(task=tasks[0])
          print(f"Task: {tasks[0]}")
        else:
          env.reset()


        # Get proxy configuration for custom browser
        proxy_config = env.get_proxy_config()
        print(f"Proxy config: {proxy_config}")

        # Launch custom browser with sync Playwright
        with sync_playwright() as p:
            # Convert proxy config to Playwright format
            playwright_proxy = None
            if proxy_config:
                server = proxy_config.get('server')
                if server:
                    playwright_proxy = ProxySettings(
                        server=server,
                        username=proxy_config.get('username'),
                        password=proxy_config.get('password')
                    )

            # Launch browser
            browser = p.chromium.launch(
                headless=False,
                proxy=playwright_proxy,
                args=[
                    "--ignore-certificate-errors",
                    "--ignore-ssl-errors",
                    "--disable-http2",
                ]
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            # Navigate to target site
            page.goto("https://transform.b4checkin.com/thecosmopolitanlv?linkId=6e5e8663b198a96d04d2ff81863f5872", timeout=30000)
            print("Navigated to GetCalFresh")

            # Wait and take screenshot
            page.wait_for_timeout(3000)
            breakpoint()
            page.screenshot(path="custom_browser_screenshot.png")
            print("Screenshot taken")

            # Get environment state
            state = env.get_state()
            print(f"Environment state: {state}")

            # Evaluate the environment
            result = env.evaluate()
            print(f"Evaluation result: {result}")

            # Keep browser open for interaction
            time.sleep(10)

            browser.close()
            print("Custom browser closed")

    finally:
        # Always ensure we close the environment
        env.close()
        print("Environment closed")
        client.close()
        print("Client closed")


if __name__ == "__main__":
    test_custom_browser_environment()
