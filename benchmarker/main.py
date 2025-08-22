import asyncio
import os
import argparse
import traceback
import logging
import uuid
import time

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

# Import for local browser support
import sys
import os

# Set PYTHONPATH environment variable for imports
plato_root = "/home/ubuntu/plato"
python_paths = [
    f"{plato_root}/core/src",
    f"{plato_root}/services/browser/src"
]
os.environ['PYTHONPATH'] = ':'.join(python_paths)

# Also add to sys.path as backup
sys.path.extend(python_paths)

from browser.browser_env import BrowserEnv
from core.schemas import ResetMessage
from core.schemas.browser import BrowserEnvironmentConfig, PlaywrightBrowserConfig, BrowserRecordingConfig
from core.schemas import CloseMessage

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


class LocalBrowserEnvironment:
    # Use a proper port pool to avoid conflicts
    _port_pool = set(range(9222, 9322))  # 100 available ports
    _port_lock = asyncio.Lock()
    
    async def _get_available_port(self):
        """Get an available port from the pool"""
        async with self._port_lock:
            if not self._port_pool:
                raise Exception("No available ports")
            port = self._port_pool.pop()
            logger.info(f"Using port {port} for browser")
            return port
    
    async def _release_port(self, port):
        """Return port to the pool"""
        async with self._port_lock:
            self._port_pool.add(port)
            logger.info(f"Released port {port}")
    
    def __init__(self, task: PlatoTask):
        self.task = task
        self.browser_env = None
        self.job_group_id = str(uuid.uuid4())
        self.session_id = None
        # Each browser environment gets a unique port
        self.cdp_port = None
    
    async def reset(self, task: PlatoTask, agent_version: str = None):
        """Reset the local browser environment"""
        self.task = task
        self.session_id = str(uuid.uuid4())
        
        # Get a unique port for this browser
        if self.cdp_port is None:
            self.cdp_port = await self._get_available_port()
        
        # Set up environment variables
        os.environ.setdefault('ENV', 'local')
        os.environ.setdefault('LOGFIRE_IGNORE_NO_CONFIG', '1')
        
        # Create BrowserEnv
        self.browser_env = BrowserEnv(self.job_group_id)
        
        # Configure browser
        from core.schemas.browser import PlaywrightBrowserConfig, BrowserRecordingConfig
        
        browser_config = PlaywrightBrowserConfig(
            browser_type="playwright",
            cdp_port=self.cdp_port,
            headless=True,
            viewport_size=(1920, 1080),
            extensions=None,
        )
        
        recording_config = BrowserRecordingConfig(
            record_rrweb=False,
            record_network_requests=False,
        )
        
        config = {
            "type": "browser",
            "job_group_id": self.job_group_id,
            "browser_config": browser_config,
            "recording_config": recording_config,
            "open_page_on_start": True,
            "js_random_seed": "local-browser",
            "start_url": self.task.start_url or "https://demo.us.espocrm.com/?l=en_US#Account",
        }
        
        # Create ResetMessage
        reset_message = ResetMessage(
            type="reset",
            session_id=self.session_id,
            log_callback_url="",
            env="local",
            config=config
        )
        
        # Retry logic for browser reset
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Browser reset attempt {attempt + 1}/{max_retries}")
                result = await self.browser_env.reset(reset_message)
                
                if not result.success:
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(f"Failed to reset local browser after {max_retries} attempts: {result.message}")
                
                logger.info(f"Browser reset successful on attempt {attempt + 1}")
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    
                    # Clean up any partial browser state
                    try:
                        if hasattr(self, 'browser_env') and self.browser_env:
                            await self.browser_env.close(CloseMessage())
                    except Exception:
                        pass
                    
                    continue
                else:
                    raise Exception(f"Failed to reset local browser after {max_retries} attempts: {str(e)}")
        
        # Wait for browser to be ready
        max_timeout = 30
        start_time = time.time()
        
        logger.info(f"Waiting for browser to become ready on port {self.cdp_port}...")
        
        while time.time() - start_time < max_timeout:
            try:
                # Check if the port is open
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', self.cdp_port))
                sock.close()
                
                if result == 0:
                    # Try to get the CDP endpoint
                    try:
                        await self.browser_env.get_browser_ws_endpoint()
                        logger.info(f"Browser ready after {time.time() - start_time:.1f}s")
                        break
                    except Exception:
                        await asyncio.sleep(2)
                        continue
                else:
                    await asyncio.sleep(1)
                    continue
                    
            except Exception:
                await asyncio.sleep(1)
                continue
        else:
            raise Exception(f"Browser failed to become ready within {max_timeout}s timeout")
        
        return self.session_id
    
    async def get_cdp_url(self) -> str:
        """Get CDP URL for local browser"""
        if not self.browser_env:
            raise Exception("Browser not initialized")
        
        # Check if browser is actually ready
        if not hasattr(self.browser_env, 'browser') or not self.browser_env.browser:
            raise Exception("Browser not ready - reset() must be called first")
            
        # Use the unique port assigned to this browser
        return f"http://127.0.0.1:{self.cdp_port}"
    
    async def get_public_url(self) -> str:
        """Return the task's start URL since we're local"""
        return self.task.start_url
    
    async def get_live_view_url(self) -> str:
        """No live view for local browser"""
        return "Local browser - no live view available"
    
    async def login(self, page):
        """Stub for login - agents will handle this"""
        pass
    
    async def log(self, item, type="message"):
        """Stub for logging - just log to console"""
        logger.info(f"Local browser log [{type}]: {item}")
    
    async def evaluate(self):
        """No evaluation for local browser"""
        return {"result": "Local browser - no evaluation available"}
    
    async def close(self):
        """Close the local browser environment"""
        if self.browser_env:
            from core.schemas import CloseMessage
            await self.browser_env.close(CloseMessage())


async def create_environment_pool(client: Plato, pool_size: int, tasks: list, use_local_browser: bool = False):
    """Create a pool of environments for reuse"""
    env_pool = asyncio.Queue()

    if use_local_browser:
        # Create local browser environments with proper cleanup
        async def create_single_local_environment(i: int):
            logger.info(f"Creating local browser environment {i+1}/{pool_size}")
            env = LocalBrowserEnvironment(tasks[0])
            # Don't initialize browser yet - wait until reset is called
            logger.info(f"Local browser environment {i+1}/{pool_size} ready")
            return env
        
        logger.info(f"Creating local browser environment pool of size {pool_size}")
        environments = []
        for i in range(pool_size):
            env = await create_single_local_environment(i)
            environments.append(env)
    else:
        # Use the first task to get env_id for creating environments
        first_task = tasks[0]

        async def create_single_environment(i: int):
            logger.info(f"Creating environment {i+1}/{pool_size}")
            env = await client.make_environment(first_task.env_id, open_page_on_start=True, record_actions=True, fast=True)
            await env.wait_for_ready()
            logger.info(f"Environment {i+1}/{pool_size} ready")
            return env

        logger.info(f"Creating environment pool of size {pool_size} in parallel")

        # Create all environments in parallel
        environments = await asyncio.gather(*[
            create_single_environment(i) for i in range(pool_size)
        ])

    # Add all environments to the pool
    for env in environments:
        await env_pool.put(env)

    logger.info(f"Environment pool of size {pool_size} created successfully")
    return env_pool, environments


async def run_with_semaphore(sem, env_pool, task, **kwargs):
    async with sem:
        try:
            await run_task(env_pool, task, **kwargs)
        except Exception as e:
            logger.error(f"Error running task: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")


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
        logger.warning(f"Error logging in: {e}")
        logger.warning(f"Traceback: {traceback.format_exc()}")
    await agent.run(max_steps=500)


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
          logger.warning(f"Error logging in: {e}")
          logger.warning(f"Traceback: {traceback.format_exc()}")
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
          logger.warning(f"Error logging in: {e}")
          logger.warning(f"Traceback: {traceback.format_exc()}")
        await agent.run(prompt, browser_tool=computer)


async def run_task(
    env_pool: asyncio.Queue,
    task: PlatoTask,
    timeout: float = 400,
    agent_version: str = "browser_use_test",
    task_set: str = "espocrm",
    use_local_browser: bool = False,
):
    logger.info(f"[{task.name}] Running task: {task.prompt}")

    # Get environment from pool
    env = await env_pool.get()
    logger.info(f"[{task.name}] Got environment from pool ({task.env_id if hasattr(task, 'env_id') else 'local'})")

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
    if not task.start_url:
        logger.warning(f"[{task.name}] Task has no start_url, using default EspoCRM URL")
        start_url = "https://demo.us.espocrm.com/?l=en_US#Account"
    else:
        start_url = task.start_url

    prompt = base_prompt.format(start_url=start_url, prompt=task.prompt)
    logger.info(f"[{task.name}] Using start_url: {start_url}")

    logger.info(f"[{task.name}] Resetting environment")
    await env.reset(task, agent_version=agent_version)
    logger.info(f"[{task.name}] Environment reset")
    
    # Verify that the browser environment is properly initialized
    if use_local_browser:
        if not hasattr(env, 'browser_env') or not env.browser_env:
            raise Exception(f"[{task.name}] Browser environment not initialized after reset")
        
        if not hasattr(env.browser_env, 'browser') or not env.browser_env.browser:
            raise Exception(f"[{task.name}] Browser not ready after reset")
        
        logger.info(f"[{task.name}] Browser environment verified ready")
    
    cdp_url = await env.get_cdp_url()
    public_url = await env.get_public_url()

    try:
        live_view_url = await env.get_live_view_url()
        logger.info(f"[{task.name}] Live view URL: {live_view_url}")

        # Double-check browser readiness before running task
        if use_local_browser:
            try:
                # Simple CDP connection test
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                port = int(cdp_url.split(':')[-1])
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result != 0:
                    raise Exception(f"CDP port {port} not accessible")
                    
                logger.info(f"[{task.name}] CDP connection verified")
            except Exception as e:
                logger.error(f"[{task.name}] Browser not ready for task execution: {e}")
                raise Exception(f"Browser not ready for task execution: {str(e)}")

        if "browser_use" in agent_version:
            await run_browseruse_task(cdp_url, prompt, public_url, env)
        elif "openai" in agent_version:
            await run_openai_cua_task(cdp_url, prompt, public_url, env)
        elif "anthropic" in agent_version:
            await run_anthropic_cua_task(cdp_url, prompt, public_url, env)

        # evaluate the task
        try:
            eval_result = await env.evaluate()
            logger.info(f"[{task.name}] Evaluation result: {eval_result}")
        except Exception as e:
            logger.error(f"[{task.name}] Error evaluating task: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    except asyncio.CancelledError:
        logger.info(f"[{task.name}] Task cancelled")
        await env.log({ "cancelled": True }, type="info")
    except Exception as e:
        await env.log({ "error": str(e) }, type="error")
        logger.error(f"[{task.name}] Error running task: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Always close the browser to free resources
        await env.close()
        
        # For local browsers, create a fresh environment
        if use_local_browser:
            new_env = LocalBrowserEnvironment(task)
            await env_pool.put(new_env)
        else:
            await env_pool.put(env)

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
    parser.add_argument(
        "--local-browser",
        action="store_true",
        help="Use local browser instead of Plato's hosted browsers",
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

    # Ask about local browser if not specified in args
    use_local_browser = args.local_browser
    if not args.local_browser:
        local_choice = input("Use local browsers instead of Plato hosted browsers? (y/n): ").lower()
        use_local_browser = local_choice == 'y'

    if use_local_browser:
        print("Using local browsers with BrowserEnv")
    else:
        print("Using Plato hosted browsers")

    # Setup semaphore for concurrency
    sem = asyncio.Semaphore(concurrency)

    # Create environment pool
    env_pool, environments = await create_environment_pool(client, concurrency, tests_to_run, use_local_browser)

    # Test the first environment if using local browsers
    if use_local_browser and environments:
        logger.info("Testing first local browser environment...")
        try:
            test_env = environments[0]
            await test_env.reset(tests_to_run[0], agent_version=agent_version)
            logger.info("Local browser environment test successful")
            
        except Exception as e:
            logger.error(f"Local browser environment test failed: {e}")
            raise Exception(f"Local browser environment test failed: {str(e)}")

    try:
        # Create tasks
        async_tasks = []
        for task in tests_to_run:
            for _ in range(num_runs):
                async_tasks.append(
                    run_with_semaphore(
                        sem, env_pool, task, timeout=400, agent_version=agent_version, task_set=selected_simulator["name"].lower(), use_local_browser=use_local_browser
                    )
                )

        # Run tasks
        print(f"\nRunning {len(async_tasks)} tasks with agent: {agent_version}")
        
        # Add error handling for task execution
        try:
            await asyncio.gather(*async_tasks)
            print("\nAll tasks completed!")
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if use_local_browser:
                logger.error("Local browser environment failed. This usually means:")
                logger.error("1. Missing system dependencies")
                logger.error("2. Playwright browsers not installed")
                logger.error("3. System doesn't support headless browsers")
                logger.error("4. Port conflicts or permission issues")
                
                # Check if any browser processes are still running
                try:
                    import subprocess
                    result = subprocess.run(['pgrep', '-f', 'chromium'], capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.error(f"Browser processes still running: {result.stdout.strip()}")
                        logger.error("Consider killing them with: pkill -f chromium")
                except Exception:
                    pass
            
            raise Exception(f"Task execution failed: {str(e)}")

    finally:
        # Close all environments in the pool
        logger.info("Closing all environments in pool")
        for env in environments:
            await env.close()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
