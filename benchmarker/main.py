import asyncio
import os
import argparse
import traceback
import logging

from browser_use import (
    Agent as BrowserUseAgent,
    Browser as BrowserUseBrowser,
    BrowserConfig as BrowserUseBrowserConfig,
    BrowserContextConfig as BrowserUseBrowserContextConfig,
)
from langchain_openai import ChatOpenAI
from plato import Plato, PlatoTask
from plato.models.env import PlatoEnvironment
from dotenv import load_dotenv
from models.anthropic.agent import AnthropicAgent
from models.anthropic.tools.computer_browser import ComputerBrowserTool20250124
from models.openai.agent.agent import Agent as OpenAIAgent

from models.openai.computers.remote_playwright import RemotePlaywrightComputer

load_dotenv(dotenv_path=".env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load required environment variables
PLATO_API_KEY = os.environ.get("PLATO_API_KEY")
if not PLATO_API_KEY:
    raise ValueError(
        "PLATO_API_KEY environment variable is not set. Please set it in your .env file."
    )

PLATO_API_URL = os.environ.get("PLATO_API_URL", "https://plato.so/api")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is not set. Please set it in your .env file."

# Task set configuration
TASK_SETS = {
    "doordash": {
        "base_prompt": """
You are a helpful assistant that can help me buy food from doordash.
start by going to {start_url}. Do not navigate to other websites.
Do not end the task until you have completed and paid for the order.
Here is the task:
{prompt}

Make sure to complete the checkout process once you've added the necessary items to cart.
The task is not complete until the order is sent and paid for.
You do not need my permission to and place an order.
""",
    },
    "espocrm": {
        "base_prompt": """
You are a helpful assistant that can help me use EspoCRM.
start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}

The login credentials are:
username: admin
password: password
""",
    },
    "roundcube": {
        "base_prompt": """
You are a helpful assistant that can help me use Roundcube webmail.
start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}

The login credentials are:
username: sarah.chen@technova.io
password: password
""",
    },
    "mattermost": {
        "base_prompt": """
You are a helpful assistant that can help me use Mattermost.
start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}

The login credentials are:
username: alex.reynolds
password: password
""",
    },
}


async def run_with_semaphore(sem, *args, **kwargs):
    async with sem:
        try:
            await run_task(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error running task: {e}", traceback.format_exc())


async def run_browseruse_task(cdp_url, prompt, start_url):
    browser = BrowserUseBrowser(
        config=BrowserUseBrowserConfig(
            cdp_url=cdp_url,
            new_context_config=BrowserUseBrowserContextConfig(
                browser_window_size={"width": 1920, "height": 1080}
            ),
        )
    )
    agent = BrowserUseAgent(
        browser=browser,
        task=prompt,
        llm=ChatOpenAI(model="gpt-4o"),
    )
    await agent.run(max_steps=40)


async def run_openai_cua_task(cdp_url, prompt, start_url, env: PlatoEnvironment):
    async with RemotePlaywrightComputer(cdp_url) as computer:
        agent = OpenAIAgent(
            computer=computer,
        )
        await computer.goto(start_url)
        async for item in agent.run_in_loop_generator(prompt, max_steps=100):
            await env.log(item)


async def run_anthropic_cua_task(cdp_url, prompt, start_url):
    async with ComputerBrowserTool20250124(cdp_url) as computer:
        agent = AnthropicAgent(
            api_key=os.getenv("ANTHROPIC_API_KEY") or "",
        )
        await computer.goto(start_url)
        await agent.run(prompt, browser_tool=computer)


async def run_task(
    client: Plato,
    task: PlatoTask,
    timeout: float = 400,
    agent_version: str = "browser_use_test",
    task_set: str = "espocrm",
):
    logger.info(f"[{task.name}] Running task: {task.prompt}")
    env = await client.make_environment(task.env_id, open_page_on_start=False)

    logger.info(f"[{task.name}] Waiting for environment to be ready ({task.env_id})")
    await env.wait_for_ready()
    logger.info(f"[{task.name}] Environment {task.env_id} is ready")

    # Get the base prompt template from the task set configuration
    base_prompt = TASK_SETS[task_set]["base_prompt"]

    # Format the prompt with task-specific information
    prompt = base_prompt.format(start_url=task.start_url, prompt=task.prompt)

    logger.info(f"[{task.name}] Resetting environment")
    await env.reset(task, agent_version=agent_version)
    logger.info(f"[{task.name}] Environment reset")
    cdp_url = await env.get_cdp_url()

    try:
        live_view_url = await env.get_live_view_url()
        logger.info(f"[{task.name}] Live view URL: {live_view_url}")

        if "browser_use" in agent_version:
            await run_browseruse_task(cdp_url, prompt, task.start_url)
        elif "openai" in agent_version:
            await run_openai_cua_task(cdp_url, prompt, task.start_url, env)
        elif "anthropic" in agent_version:
            await run_anthropic_cua_task(cdp_url, prompt, task.start_url)

        # evaluate the task
        try:
            eval_result = await env.evaluate()
            logger.info(f"[{task.name}] Evaluation result: {eval_result}")
        except Exception as e:
            logger.error(f"[{task.name}] Error evaluating task: {e}", traceback.format_exc())

    except asyncio.CancelledError:
        logger.info(f"[{task.name}] Task cancelled")
        await env.log({ "cancelled": True }, type="info")
    except Exception as e:
        await env.log({ "error": str(e) }, type="error")
        logger.error(f"[{task.name}] Error running task: {e}", traceback.format_exc())
    finally:
        logger.info(f"[{task.name}] Closing environment")
        await env.close()

async def main():
    """
    go through steps of getting user input.
    - agent version
    - simulator (fetch list from plato.list_simulators())
    - task(s) can either run all or specific ones (fetch list from plato.list_simulator_tasks(simulator_id))
    - runs (int)
    - concurrency (int)
    """
        # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run Plato benchmark tasks")
    parser.add_argument(
        "--simulator",
        type=str,
        default=None,
        help="Simulator name to run tasks from",
        required=False,
    )
    parser.add_argument(
        "--task-name",
        type=str,
        default=None,
        help="Specific task name to run (if not specified, all tasks in the simulator will run)",
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all available tasks in the specified simulator and exit",
    )
    parser.add_argument("--runs", type=int, help="Number of runs per task")
    parser.add_argument(
        "--concurrency", type=int, help="Number of concurrent tasks"
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=[
            "browser_use",
            "anthropic",
            "openai_cua",
        ],
        help="Agent to use for the tasks",
    )
    parser.add_argument(
        "--tag",
        type=str,
        help="Tag for agent version, ex: '20250423'",
    )
    args = parser.parse_args()

    client = Plato(base_url=PLATO_API_URL, api_key=PLATO_API_KEY)

    # Get available simulators
    simulators = await client.list_simulators()
    print("Available simulators:")
    for i, simulator in enumerate(simulators):
        print(f"{simulator['name']}")


    selected_simulator_name = None
    if args.simulator:
        selected_simulator = next(s for s in simulators if s["name"] == args.simulator)
        selected_simulator_name = selected_simulator["name"]
    else:
        while not selected_simulator_name:
          simulator_choice = input("Select simulator (name): ")
          selected_simulator = next(s for s in simulators if s["name"] == simulator_choice)
          selected_simulator_name = selected_simulator["name"]

    # Get tasks for the selected simulator
    simulator_tasks = await client.load_tasks(selected_simulator_name)

    for task in simulator_tasks:
        print(f"{task.name}")

    task_choice = args.task_name or input("Input comma separated task names or 'all' for all tasks: ")
    if task_choice.lower() == 'all':
        tests_to_run = simulator_tasks
    else:
        task_names = task_choice.split(",")
        tests_to_run = [t for t in simulator_tasks if t.name in task_names]

    if args.agent:
        agent_version = args.agent
    else:
        # Get agent version
        print("\nAgent options:")
        print("1. browser_use")
        print("2. anthropic")
        print("3. openai_cua")
        agent_choice = int(input("Select agent (number): "))
        agent_versions = ["browser_use", "anthropic", "openai_cua"]
        agent_version = agent_versions[agent_choice-1]

        tag = input("Enter optional tag for agent version (press enter to skip): ")
        if tag:
            agent_version = f"{agent_version}_v{tag}"

    # Get runs and concurrency
    num_runs = args.runs or int(input("Enter number of runs per task: ") or "1")
    concurrency = args.concurrency or int(input("Enter concurrency (max parallel tasks): ") or "5")

    # Setup semaphore for concurrency
    sem = asyncio.Semaphore(concurrency)

    # Create tasks
    async_tasks = []
    for task in tests_to_run:
        for _ in range(num_runs):
            async_tasks.append(
                run_with_semaphore(
                    sem, client, task, agent_version=agent_version, task_set=selected_simulator["name"].lower()
                )
            )

    # Run tasks
    print(f"\nRunning {len(async_tasks)} tasks with agent: {agent_version}")
    await asyncio.gather(*async_tasks)

    print("\nAll tasks completed!")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
