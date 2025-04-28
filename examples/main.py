import asyncio
import os
import argparse
import traceback
import logging
import colorlog

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
from plato.examples.doordash_tasks import all_tasks as doordash_tasks
from plato.examples.espocrm_tasks import all_tasks as espocrm_tasks
from plato.examples.roundcube_tasks import all_tasks as roundcube_tasks
from plato.examples.mattermost_tasks import all_tasks as mattermost_tasks

from models.openai.computers.remote_playwright import RemotePlaywrightComputer

load_dotenv(dotenv_path=".env")

# Configure colorful logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicate logs
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
        'TASK': 'white,bold',
    },
    secondary_log_colors={},
    style='%'
))
logger.addHandler(handler)

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
        "tasks": doordash_tasks,
        "base_prompt": """
You are a helpful assistant that can help me buy food from doordash.
start by going to {start_url}. Do not navigate to other websites.
While you can't finish the checkout process becuase you need user permission,
you can add items to cart and see the total price. Do not end the task until you have added the necessary items to cart.
Here is the task:
{prompt}

Make sure to complete the checkout process once you've added the necessary items to cart.
The task is not complete until the order is sent and paid for.
You do not need my permission to and place an order.
""",
    },
    "espocrm": {
        "tasks": espocrm_tasks,
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
        "tasks": roundcube_tasks,
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
        "tasks": mattermost_tasks,
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
    logger.info(f"\033[1m[{task.name}]\033[0m Running task: {task.prompt}")
    env = await client.make_environment(task.env_id, open_page_on_start=False)

    logger.info(f"\033[1m[{task.name}]\033[0m Waiting for environment to be ready ({task.env_id})")
    await env.wait_for_ready()
    logger.info(f"\033[1m[{task.name}]\033[0m Environment {task.env_id} is ready")

    # Get the base prompt template from the task set configuration
    base_prompt = TASK_SETS[task_set]["base_prompt"]

    # Format the prompt with task-specific information
    prompt = base_prompt.format(start_url=task.start_url, prompt=task.prompt)

    logger.info(f"\033[1m[{task.name}]\033[0m Resetting environment")
    await env.reset(task, agent_version=agent_version)
    logger.info(f"\033[1m[{task.name}]\033[0m Environment reset")
    cdp_url = await env.get_cdp_url()

    try:
        live_view_url = await env.get_live_view_url()
        logger.info(f"\033[1m[{task.name}]\033[0m Live view URL: {live_view_url}")

        if "browser_use" in agent_version:
            await run_browseruse_task(cdp_url, prompt, task.start_url)
        elif "openai" in agent_version:
            await run_openai_cua_task(cdp_url, prompt, task.start_url, env)
        elif "anthropic" in agent_version:
            await run_anthropic_cua_task(cdp_url, prompt, task.start_url)

        # evaluate the task
        eval_result = await env.evaluate()
        logger.info(f"\033[1m[{task.name}]\033[0m Evaluation result: {eval_result}")

    except asyncio.CancelledError:
        logger.info(f"\033[1m[{task.name}]\033[0m Task cancelled")
    except Exception as e:
        logger.error(f"\033[1m[{task.name}]\033[0m Error running task: {e}", traceback.format_exc())
    finally:
        logger.info(f"\033[1m[{task.name}]\033[0m Closing environment")
        await env.close()
        logger.info(f"\033[1m[{task.name}]\033[0m Closing client")
        await client.close()


async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run Plato benchmark tasks")
    parser.add_argument(
        "--task-set",
        type=str,
        choices=list(TASK_SETS.keys()),
        default=None,
        help="Task set to run",
        required=True,
    )
    parser.add_argument(
        "--task-name",
        type=str,
        default=None,
        help="Specific task name to run (if not specified, all tasks in the set will run)",
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all available tasks in the specified task set and exit",
    )
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per task")
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Number of concurrent tasks"
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=[
            "browser_use",
            "anthropic",
            "openai_cua",
        ],
        default="browser_use",
        help="Agent to use for the tasks",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Tag for agent version, ex: '20250423'",
    )
    args = parser.parse_args()
    all_tasks = TASK_SETS[args.task_set]["tasks"]

    # If --list-tasks is specified, print available tasks and exit
    if args.list_tasks:
        task_names = [task.name for task in all_tasks]
        logger.info(f"Available tasks in '{args.task_set}' task set:")
        for name in sorted(task_names):
            logger.info(f"  - {name}")
        return

    # Initialize Plato client with API URL and key from environment variables
    client = Plato(base_url=PLATO_API_URL, api_key=PLATO_API_KEY)

    num_concurrent = args.concurrency
    sem = asyncio.Semaphore(num_concurrent)

    num_runs_per_task = args.runs
    agent_version = args.agent + (f"_v{args.tag}" if args.tag else "")
    task_set = args.task_set

    # Filter tasks if a specific task name is provided
    if args.task_name:
        tasks_to_run = [task for task in all_tasks if task.name == args.task_name]
        if not tasks_to_run:
            available_tasks = [task.name for task in all_tasks]
            logger.error(
                f"Error: Task '{args.task_name}' not found in task set '{task_set}'."
            )
            logger.error(f"Available tasks: {', '.join(available_tasks)}")
            return
    else:
        tasks_to_run = all_tasks

    async_tasks = []
    for task in tasks_to_run:
        for _ in range(num_runs_per_task):
            async_tasks.append(
                run_with_semaphore(
                    sem, client, task, agent_version=agent_version, task_set=task_set
                )
            )
    await asyncio.gather(*async_tasks)


if __name__ == "__main__":
    asyncio.run(main())
