"""This module contains tests for the Plato client, including session management and task execution."""

import asyncio

from plato import Plato

plato = Plato(
    api_key="22493513-f909-4fef-8aaf-8af2c46dcf1c", base_url="http://localhost:25565"
)


async def test_plato_client_start_session():
    """Test the Plato client by starting a session and performing a series of actions on a website, such as navigating, clicking, and typing."""
    session = plato.start_session()

    try:
        print(session.navigate("https://www.amazon.com"))
        print(session.click("the search bar"))
        print(session.type("chocolate soylent [Enter]"))
        print(session.click("the first result"))
        print(session.click('the "add to cart" button'))

    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        session.end()


async def test_plato_client_task():
    """Test the Plato client by starting a session and performing a task on a website.

    This function starts a session, performs a task to add chocolate soylent to the cart on Amazon,
    and handles any exceptions that may occur during the process. Finally, it ends the session.
    """
    session = plato.start_session()

    try:
        print(session.task("add chocolate soylent to cart", "https://www.amazon.com"))

    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        session.end()


# def test_playwright():
#   from playwright.sync_api import sync_playwright
#   session = plato.start_session()
#   try:
#     with sync_playwright() as p:
#       browser = p.chromium.connect_over_cdp(session.chrome_ws_url)
#       page = browser.new_page()
#       page.goto("https://www.amazon.com")
#       page.screenshot(path="screenshot.png")
#   except Exception as e:
#     print('ERROR',e)
#   finally:
#     session.end()


if __name__ == "__main__":
    asyncio.run(test_plato_client_task())
    # test_playwright()
