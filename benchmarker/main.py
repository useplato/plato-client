import asyncio
import os
import argparse
import traceback
import logging
import csv
import json
import httpx

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
from plato.examples.craigslist_tasks import all_tasks as craigslist_tasks
from plato.examples.craigslist_tasks import craigslist_eval_tasks

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

PLATO_API_URL = os.environ.get("PLATO_API_URL", "http://localhost:8080/api")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is not set. Please set it in your .env file."

# Task set configuration
TASK_SETS = {
    "doordash": {
        "tasks": doordash_tasks,
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
        "tasks": espocrm_tasks[::-1],
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
    "craigslist": {
        "tasks": craigslist_tasks,
        "base_prompt": """
You are a helpful assistant that can help me shop on Craigslist.com.
Start by going to {start_url}. Do not navigate to other websites.
Here is the task:
{prompt}

The task is not complete until the required items are in the cart or the objective is met.
You do not need my permission to add items to the cart.
""",
    },
}


async def run_with_semaphore(sem, *args, **kwargs):
    async with sem:
        try:
            return await run_task(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error running task: {e}", traceback.format_exc())
            return None


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
        llm=ChatOpenAI(model="gpt-4.1"),
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
    record_network_requests: bool = False,
    passthrough: bool = False,
):
    logger.info(f"[{task.name}] Running task: {task.prompt}")
    env = await client.make_environment(task.env_id, open_page_on_start=False, record_network_requests=record_network_requests, passthrough=passthrough)

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

    # Placeholder for run_session_id. Assuming env.id is the identifier.
    # This might need adjustment based on how PlatoEnvironment exposes the run session's unique ID.
    run_session_id = env._run_session_id 
    logger.info(f"[{task.name}] Current run session ID: {run_session_id}")

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
        # Removed: await client.close() - Client should be closed at the end of main
        logger.info(f"[{task.name}] Client NOT closed here, will be closed in main.")

    return run_session_id

async def calculate_ood_requests(run_session_ids_results) -> tuple[int, int]:
    total_runs_for_csv = 0
    ood_requests_overall = 0

    async with httpx.AsyncClient() as http_client:
        for session_id in run_session_ids_results:
            if session_id:
                total_runs_for_csv += 1
                try:
                    logs_url = f"{PLATO_API_URL}/session/{session_id}"
                    headers = {"X-API-Key": PLATO_API_KEY}

                    logger.info(f"Fetching logs for run_session_id: {session_id} from {logs_url}")
                    response = await http_client.get(logs_url, headers=headers)
                    response.raise_for_status()
                    
                    logs = response.json()
                    logs_list = logs.get("logs")

                    session_ood_requests = 0
                    if logs_list and isinstance(logs_list, list):
                        for log_entry in logs_list:
                            if isinstance(log_entry, dict) and "logData" in log_entry:
                                log_data_str = log_entry.get("logData")
                                try:
                                    if isinstance(log_data_str, str):
                                        parsed_log_data = json.loads(log_data_str)
                                    elif isinstance(log_data_str, dict):
                                        parsed_log_data = log_data_str
                                    else:
                                        parsed_log_data = {}

                                    if parsed_log_data.get("type") == "ood_request":
                                        session_ood_requests += 1
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse log_data JSON for session {session_id}: {log_data_str}")
                                except Exception as e:
                                    logger.warning(f"Error processing log_data for session {session_id}: {e}")

                        logger.info(f"Found {session_ood_requests} OOD requests for session_id: {session_id}")
                        ood_requests_overall += session_ood_requests
                    else:
                        logger.warning(f"Unexpected log format for session {session_id}. Expected a list, got {type(logs)}")

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error fetching logs for session {session_id}: {e.response.status_code} - {e.response.text}")
                except httpx.RequestError as e:
                    logger.error(f"Request error fetching logs for session {session_id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing logs for session {session_id}: {e}", traceback.format_exc())
            else:
                logger.warning("A task run failed or did not return a session_id. Skipping log processing for it.")

    return total_runs_for_csv, ood_requests_overall

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
        "--record-network-requests",
        type=str,
        default=None,
        help="Enable or disable network request recording ('true' or 'false'). If not set, uses SDK/server default."
    )
    parser.add_argument(
        "--passthrough",
        type=str,
        default=None,
        help="Enable or disable passthrough to the agent, ex: 'true' or 'false'"
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
    # DO NOT COMMIT THIS
    simulator_tasks = TASK_SETS[selected_simulator_name]["tasks"]

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

    if args.record_network_requests is not None:
        record_network_requests = args.record_network_requests == "true"
    else:
        record_network_requests = input("Record network requests? (y/n): ") == "y"

    if args.passthrough:
        passthrough = args.passthrough == "true"
    else:
        passthrough = input("Passthrough to the agent? (y/n): ") == "y"

    # Setup semaphore for concurrency
    sem = asyncio.Semaphore(concurrency)

    # Create tasks
    async_tasks = []
    for task in tests_to_run:
        for _ in range(num_runs):
            async_tasks.append(
                run_with_semaphore(
                    sem, client, task, agent_version=agent_version, task_set=selected_simulator["name"].lower(), record_network_requests=record_network_requests, passthrough=passthrough
                )
            )

    # Run tasks
    print(f"\nRunning {len(async_tasks)} tasks with agent: {agent_version}")
    run_session_ids_results = await asyncio.gather(*async_tasks)

    print("\nAll tasks completed!")

    # only calculate OOD requests for eval runs
    if not passthrough:
        total_runs_for_csv, ood_requests_overall = await calculate_ood_requests(run_session_ids_results)

        logger.info(
            f"CSV Logging: Total runs processed for logs = {total_runs_for_csv}. OOD Requests Overall = {ood_requests_overall}."
        )

        csv_file_name = "ood_stats.csv"
        try:
            with open(csv_file_name, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["total_runs", "ood_requests_overall"])
                writer.writerow([total_runs_for_csv, ood_requests_overall])
            logger.info(f"OOD statistics saved to {csv_file_name}")
        except IOError as e:
            logger.error(f"Failed to write OOD statistics to CSV {csv_file_name}: {e}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
