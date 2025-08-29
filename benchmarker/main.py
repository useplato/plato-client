import asyncio
import os
import argparse
import traceback
import logging
import requests

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

PLATO_BASE_URL = os.environ.get("PLATO_BASE_URL", "https://plato.so/api")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is not set. Please set it in your .env file."

# Anchor Browser configuration
ANCHOR_API_KEY = os.environ.get("ANCHOR_API_KEY")
ANCHOR_API_URL = os.environ.get("ANCHOR_API_URL", "https://api.anchorbrowser.io/v1")

if not ANCHOR_API_KEY:
    logger.warning("ANCHOR_API_KEY not set; Anchor browser sessions will fail to create")

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
    "snipeit": {
        "base_prompt": """
You are a helpful assistant that can help me use Snipe-IT.
start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}

The login credentials are:
username: mrudulplato
password: platodev
""",
    },
    "taiga": {
        "base_prompt": """
You are a helpful assistant that can help me use Taiga.
start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}
The login credentials are:
username: admin
password: admin
""",
    },
    "suitecrm": {
        "base_prompt": """
You are a helpful assistant that can help me use SuiteCRM.
start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}

The login credentials are:
username: user
password: bitnami
""",
    },
    "getcalfresh": {
        "base_prompt": """
You are a helpful assistant that can help me use GetCalFresh.
start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}
""",
    },
}


async def create_concurrency_controllers(pool_size: int):
    """Create semaphores to control concurrent environment creation"""
    # Each semaphore allows only 1 task to create an environment at a time
    semaphores = [asyncio.Semaphore(1) for _ in range(pool_size)]
    return semaphores


async def run_with_concurrency_limit(sem, client, *args, **kwargs):
    async with sem:
        try:
            await run_task(client, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error running task: {e}", exc_info=True)


async def run_browseruse_task(cdp_url, prompt, start_url, env: PlatoEnvironment):
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
    page = await agent.browser_context.get_current_page()
    # # page = await playwright_browser.new_page()
    await page.goto(start_url)
    await page.wait_for_load_state("networkidle")
    try:
        await env.login(page)
    except Exception as e:
        logger.warning(f"Error logging in: {e}", exc_info=True)
    await agent.run(max_steps=500)


async def _create_anchor_session() -> tuple[str, str]:
    """Create an Anchor browser session and return (cdp_url, session_id)."""
    def _post():
        headers = {"anchor-api-key": ANCHOR_API_KEY or "", "Content-Type": "application/json"}
        resp = requests.post(f"{ANCHOR_API_URL}/sessions", headers=headers, timeout=300)
        resp.raise_for_status()
        data = resp.json()["data"]
        return data["cdp_url"], data["id"]

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _post)


async def _delete_anchor_session(session_id: str) -> None:
    """Best-effort delete of Anchor browser session."""
    def _delete():
        try:
            requests.delete(f"{ANCHOR_API_URL}/sessions/{session_id}", timeout=20)
        except Exception:
            pass

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _delete)


async def run_openai_cua_task(cdp_url, prompt, start_url, env: PlatoEnvironment):
    async with RemotePlaywrightComputer(cdp_url) as computer:
        agent = OpenAIAgent(
            computer=computer,
        )
        await computer.goto(start_url)
        page = computer._page
        try:
          await env.login(page)
        except Exception as e:
          logger.warning(f"Error logging in: {e}", exc_info=True)
        async for item in agent.run_in_loop_generator(prompt, max_steps=100):
            await env.log(item)


async def run_anthropic_cua_task(cdp_url, prompt, start_url, env: PlatoEnvironment):
    async with ComputerBrowserTool20250124(cdp_url) as computer:
        agent = AnthropicAgent(
            api_key=os.getenv("ANTHROPIC_API_KEY") or "",
        )
        page = computer._page
        await computer.goto(start_url)
        try:
          await env.login(page)
        except Exception as e:
          logger.warning(f"Error logging in: {e}", exc_info=True)
        await agent.run(prompt, browser_tool=computer)


async def run_task(
    client: Plato,
    task: PlatoTask,
    timeout: float = 400,
    agent_version: str = "browser_use_test",
    task_set: str = "espocrm",
):
    logger.info(f"[{task.name}] Running task: {task.prompt}")
    logger.info(f"[{task.name}] Creating New Environment For Task: ({task.env_id})")
    env = await client.make_environment(task.env_id, open_page_on_start=True, interface_type=None, record_actions=True, fast=True)
    await env.wait_for_ready(timeout=30)
    logger.info(f"[{task.name}] Environment ready")

    # Get the base prompt template from the task set configuration
    if task_set in TASK_SETS:
        base_prompt = TASK_SETS[task_set]["base_prompt"]
    else:
        base_prompt = f"""
        You are a helpful assistant that can help me use the {task_set}.
        Do not navigate to other websites.
        Here is the task:
        {task.prompt}
        """

    # Format the prompt with task-specific information
    prompt = base_prompt.format(start_url=task.start_url, prompt=task.prompt)

    logger.info(f"[{task.name}] Resetting environment {agent_version}")
    await env.reset(task, agent_version=agent_version)
    logger.info(f"[{task.name}] Environment reset")
    # Use Anchor browser instead of environment-provided CDP
    logger.info(f"[{task.name}] Creating Anchor browser session")
    anchor_cdp_url = None
    anchor_session_id = None
    try:
        anchor_cdp_url, anchor_session_id = await _create_anchor_session()
        logger.info(f"[{task.name}] Anchor session created: {anchor_session_id}")
    except Exception as e:
        logger.error(f"[{task.name}] Failed to create Anchor session: {e}")
        raise
    public_url = await env.get_public_url()

    try:
        live_view_url = await env.get_live_view_url()
        logger.info(f"[{task.name}] Live view URL: {live_view_url}")

        if "browser_use" in agent_version:
            await run_browseruse_task(anchor_cdp_url, prompt, public_url, env)
        elif "openai" in agent_version:
            await run_openai_cua_task(anchor_cdp_url, prompt, public_url, env)
        elif "anthropic" in agent_version:
            await run_anthropic_cua_task(anchor_cdp_url, prompt, public_url, env)

        # evaluate the task
        try:
            eval_result = await env.evaluate()
            logger.info(f"[{task.name}] Evaluation result: {eval_result}")
        except Exception as e:
            logger.error(f"[{task.name}] Error evaluating task: {e}\n{traceback.format_exc()}")

    except asyncio.CancelledError:
        logger.info(f"[{task.name}] Task cancelled")
        await env.log({ "cancelled": True }, type="info")
    except Exception as e:
        await env.log({ "error": str(e) }, type="error")
        logger.error(f"[{task.name}] Error running task: {e}\n{traceback.format_exc()}")
    finally:
        if anchor_session_id:
            logger.info(f"[{task.name}] Deleting Anchor session: {anchor_session_id}")
            await _delete_anchor_session(anchor_session_id)
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
    parser.add_argument(
        "--max-num-validator-human-scores",
        type=int,
        help="Filter tasks to only include those where num_validator_human_scores <= this value",
    )
    args = parser.parse_args()

    client = Plato(api_key=PLATO_API_KEY, base_url=PLATO_BASE_URL)

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

    # Filter tasks based on max_num_validator_human_scores if specified
    if args.max_num_validator_human_scores is not None:
        original_count = len(simulator_tasks)
        simulator_tasks = [
            task for task in simulator_tasks
            if task.num_validator_human_scores is None or (task.num_validator_human_scores > 0 and task.num_validator_human_scores <= args.max_num_validator_human_scores)
        ]
        filtered_count = len(simulator_tasks)
        print(f"Filtered tasks: {original_count} -> {filtered_count} (max_num_validator_human_scores <= {args.max_num_validator_human_scores})")

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

    tag = args.tag or input("Enter optional tag for agent version (press enter to skip): ")
    if tag:
        agent_version = f"{agent_version}_v{tag}"

    # Get runs and concurrency
    num_runs = args.runs or int(input("Enter number of runs per task: ") or "1")
    concurrency = args.concurrency or int(input("Enter concurrency (max parallel tasks): ") or "5")

    # Setup concurrency controllers
    concurrency_semaphores = await create_concurrency_controllers(concurrency)

    try:
        # Create tasks
        async_tasks = []
        for i, task in enumerate(tests_to_run):
            for run_num in range(num_runs):
                # Distribute tasks across available semaphores for better concurrency
                semaphore_index = (i * num_runs + run_num) % len(concurrency_semaphores)
                async_tasks.append(
                    run_with_concurrency_limit(
                        concurrency_semaphores[semaphore_index], client, task, agent_version=agent_version, task_set=selected_simulator_name.lower()
                    )
                )

        # Run tasks
        print(f"\nRunning {len(async_tasks)} tasks with agent: {agent_version}")
        await asyncio.gather(*async_tasks)

        print("\nAll tasks completed!")
    finally:
        # Each task closes its own environment, so no cleanup needed here
        logger.info("All tasks completed and environments closed")
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
