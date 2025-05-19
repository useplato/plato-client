import asyncio
import os
import sys
from pathlib import Path


# Add parent directory to path to import from models
sys.path.append(str(Path(__file__).parent.parent))

from models.openai.computers.remote_playwright import RemotePlaywrightComputer
from models.anthropic.agent import AnthropicAgent
from models.anthropic.tools.computer_browser import ComputerBrowserTool20250124
from playwright.async_api import async_playwright
from models.openai.agent.agent import Agent as OpenAIAgent
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

async def run_anthropic_cua_task(cdp_url, prompt, start_url):
    async with ComputerBrowserTool20250124(cdp_url) as computer:
        agent = AnthropicAgent(
            api_key=os.getenv("ANTHROPIC_API_KEY") or "",
        )
        await computer.goto(start_url)
        await agent.run(prompt, browser_tool=computer)


async def run_single_turn(cdp_url, prompt, start_url):
    async with RemotePlaywrightComputer(cdp_url) as computer:
        agent = OpenAIAgent(
            computer=computer,
        )
        await computer.goto(start_url)
        items, actions = await agent.run_single_action(prompt, n_samples=15)
        breakpoint()

        async def get_action_xpath(action):
          if isinstance(action, dict) and "type" in action and action["type"] == "click":  # type: ignore
              if "x" in action and "y" in action and computer._page is not None:
                  x = action["x"]  # type: ignore
                  y = action["y"]  # type: ignore
                  # get the DOM element at this position
                  # Get XPath for the element using a JavaScript function to generate XPath
                  element_xpath = await computer._page.evaluate("""(function() {
                    var element = document.elementFromPoint(""" + str(x) + """, """ + str(y) + """);
                    if (!element) return null;

                    function getXPath(node) {
                      if (node.id) {
                        return '//*[@id="' + node.id + '"]';
                      }
                      var parts = [];
                      while (node && node.nodeType === 1) {  // 1 is Node.ELEMENT_NODE
                        var index = 1;
                        var sibling = node.previousSibling;
                        while (sibling) {
                          if (sibling.nodeType === 1 && sibling.nodeName === node.nodeName) {
                            index++;
                          }
                          sibling = sibling.previousSibling;
                        }
                        var tagName = node.nodeName.toLowerCase();
                        var pathIndex = index > 1 ? '[' + index + ']' : '';
                        parts.unshift(tagName + pathIndex);
                        node = node.parentNode;
                      }
                      return '/' + parts.join('/');
                    }

                    return getXPath(element);
                  })()""")
              return element_xpath


        for action in actions:
            element_xpath = await get_action_xpath(action)
            action["element_xpath"] = element_xpath


        return items, actions


async def main():
    # Default values - these could be passed via command line arguments
    prompt = "You are on airbnb.com. Find a place to stay in New York City for the dates June 3rd-6th."
    start_url = "https://www.airbnb.com"

    # Launch browser with Playwright first
    async with async_playwright() as p:
        # Launch browser with Chrome DevTools Protocol (CDP) enabled
        browser = await p.chromium.launch(headless=False, args=['--remote-debugging-port=9222'])

        # Get the CDP URL
        cdp_url = "http://localhost:9222"

        # Run the task 20 times in parallel
        results = await run_single_turn(cdp_url, prompt, start_url)

        for action in results[1]:
            print(action)

        # Keep browser open for debugging if needed
        print("Press Enter to close the browser...")
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Close the browser
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
