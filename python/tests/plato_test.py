import asyncio
from plato.plato_client import PlatoClient, PlatoConfig


async def test_plato_client_start_session():
  config = PlatoConfig(api_key="22493513-f909-4fef-8aaf-8af2c46dcf1c")
  session = PlatoClient.start_session(config)

  try:
    print(session.navigate("https://www.amazon.com"))
    print(session.click("the search bar"))
    print(session.type("chocolate soylent [Enter]"))
    print(session.click("the first result"))
    print(session.click("the \"add to cart\" button"))

  except Exception as e:
    import traceback
    traceback.print_exc()
  finally:
    session.end()


# def test_playwright():
#   from playwright.sync_api import sync_playwright
#   session = PlatoClient.start_session(PlatoConfig(api_key="22493513-f909-4fef-8aaf-8af2c46dcf1c"))
#   try:
#     with sync_playwright() as p:
#       browser = p.chromium.connect_over_cdp(session.browser_ws_url)
#       page = browser.new_page()
#       page.goto("https://www.amazon.com")
#       page.screenshot(path="screenshot.png")
#   except Exception as e:
#     print('ERROR',e)
#   finally:
#     session.end()



if __name__ == "__main__":
  asyncio.run(test_plato_client_start_session())
  # test_playwright()
