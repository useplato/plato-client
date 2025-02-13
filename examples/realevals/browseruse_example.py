import argparse
import asyncio
import logging
import os

from browser_use import (
    Agent,
    Browser,
    BrowserConfig,
)
from browser_use.browser.context import BrowserSession, BrowserState
from browser_use.dom.views import DOMElementNode
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from plato.client import Plato, PlatoRunnerConfig
from plato.models import Task

API_KEY = "6c25af04-1ae2-4715-bd67-84cc33e875ce"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO)

load_dotenv()


async def run_browseruse_agent(task: Task, cdp_url: str):
    logger.info(f"Running browseruse agent for task: {task}")
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    browser = Browser(config=BrowserConfig(cdp_url=cdp_url))
    playwright_browser = await browser.get_playwright_browser()
    browser_context = await browser.new_context()

    playwright_browser = await browser.get_playwright_browser()

    context = await browser_context._create_context(playwright_browser)
    browser_context._add_new_page_listener(context)
    pages = context.pages

    page = pages[0]
    initial_state = BrowserState(
        element_tree=DOMElementNode(
            tag_name="root",
            is_visible=True,
            parent=None,
            xpath="",
            attributes={},
            children=[],
        ),
        selector_map={},
        url=page.url,
        title=await page.title(),
        screenshot=None,
        tabs=[],
    )

    browser_context.session = BrowserSession(
        context=context,
        current_page=page,
        cached_state=initial_state,
    )

    agent = Agent(
        task=task.prompt,
        browser=browser,
        browser_context=browser_context,
        llm=llm,
    )

    async def timeout_handler(timeout_event: asyncio.Event):
        await asyncio.sleep(300.0)
        timeout_event.set()

    async def run_with_timeout():
        try:
            timeout_event = asyncio.Event()
            timeout_task = asyncio.create_task(timeout_handler(timeout_event))
            agent_task = asyncio.create_task(agent.run(max_steps=10))

            # wait for the timeout or the agent task to finish first
            done, pending = await asyncio.wait(
                [agent_task, timeout_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if agent_task in done:
                return await agent_task
        finally:
            await page.close()

    return await run_with_timeout()


async def main():
    parser = argparse.ArgumentParser(description="Run test cases in a batch")
    parser.add_argument(
        "--test-case-set-id",
        type=int,
        required=True,
        help="ID of the test case set to run",
    )
    parser.add_argument(
        "--batch-name", type=str, default="Test Batch", help="Name for the batch run"
    )
    parser.add_argument(
        "--agent-version",
        type=str,
        required=True,
        help="Version of the CDP URL agent",
    )
    args = parser.parse_args()

    # Get test cases from dataset
    test_cases = await Plato.get_dataset(
        str(args.test_case_set_id), api_key=API_KEY, base_url="http://localhost:25565"
    )

    """
    Test case example:
    {
        "name": "Staynb - Find total price for 2-night stay",
        "prompt": "What is the total price for a 2-night stay at the Mountain View Cottage?",
        "start_url": "https://evals-staynb.vercel.app/",
        "default_scoring_config": {
            "type": "real_eval_scorer",
            "reference_response": "$420"  # Example response to check against
        },
        "config": {
            "challenge_type": "retrieval",
            "difficulty": "easy",
            "website": "staynb"
        }
    }
    """

    # Create a run group for this batch
    config = PlatoRunnerConfig(
        name=args.batch_name,
        data=test_cases,
        task=run_browseruse_agent,
        trial_count=1,
        timeout=180000,  # 3 minutes
        max_concurrency=1,  # Run one at a time
    )

    await Plato.start(
        args.agent_version, config, API_KEY, base_url="http://localhost:25565"
    )


if __name__ == "__main__":
    asyncio.run(main())
