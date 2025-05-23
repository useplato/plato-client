import asyncio
import os
import traceback
import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(title="Plato Benchmarker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
}


class BenchmarkRequest(BaseModel):
    testcase_ids: List[str]
    agent: str
    version: Optional[str] = None
    runs: int = 1
    concurrency: int = 5
    base_url: Optional[str] = None


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
        elif "anthropic" in agent_version or "claude" in agent_version:
            await run_anthropic_cua_task(cdp_url, prompt, task.start_url)

        # evaluate the task
        try:
            eval_result = await env.evaluate()
            logger.info(f"[{task.name}] Evaluation result: {eval_result}")
            return eval_result
        except Exception as e:
            logger.error(f"[{task.name}] Error evaluating task: {e}", traceback.format_exc())
            return {"error": str(e)}

    except asyncio.CancelledError:
        logger.info(f"[{task.name}] Task cancelled")
        await env.log({"cancelled": True}, type="info")
        return {"cancelled": True}
    except Exception as e:
        await env.log({"error": str(e)}, type="error")
        logger.error(f"[{task.name}] Error running task: {e}", traceback.format_exc())
        return {"error": str(e)}
    finally:
        logger.info(f"[{task.name}] Closing environment")
        await env.close()


async def run_with_semaphore(sem, *args, **kwargs):
    async with sem:
        try:
            return await run_task(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error running task: {e}", traceback.format_exc())
            return {"error": str(e)}


async def run_benchmark_background(request: BenchmarkRequest):
    """
    Background task to run benchmark tasks
    """
    try:
        api_url = request.base_url or PLATO_API_URL
        client = Plato(base_url=api_url, api_key=PLATO_API_KEY)

        # Get available simulators
        simulators = await client.list_simulators()

        # Find tasks by testcase_ids
        all_tasks = []
        for simulator in simulators:
            simulator_tasks = await client.load_tasks(simulator["name"])
            for task in simulator_tasks:
                if task.public_id in request.testcase_ids:
                    all_tasks.append((task, simulator["name"].lower()))

        if not all_tasks:
            logger.error("No tasks found for the provided testcase_ids")
            return

        # Build agent version string
        agent_version = request.agent
        if request.version:
            agent_version = f"{request.agent}_v{request.version}"

        # Setup semaphore for concurrency
        sem = asyncio.Semaphore(request.concurrency)

        # Create async tasks
        async_tasks = []
        for task, task_set in all_tasks:
            for _ in range(request.runs):
                async_tasks.append(
                    run_with_semaphore(
                        sem, client, task, agent_version=agent_version, task_set=task_set
                    )
                )

        # Run tasks
        logger.info(f"Running {len(async_tasks)} tasks with agent: {agent_version}")
        results = await asyncio.gather(*async_tasks)

        await client.close()
        logger.info(f"Completed {len(async_tasks)} tasks")

    except Exception as e:
        logger.error(f"Error in background benchmark task: {e}", traceback.format_exc())


@app.post("/benchmark")
async def benchmark_tasks(request: BenchmarkRequest, background_tasks: BackgroundTasks):
    """
    Start benchmark tasks as a background job and return immediately
    """
    try:
        # Validate that tasks exist before starting background job
        api_url = request.base_url or PLATO_API_URL
        client = Plato(base_url=api_url, api_key=PLATO_API_KEY)
        
        simulators = await client.list_simulators()
        all_tasks = []
        for simulator in simulators:
            simulator_tasks = await client.load_tasks(simulator["name"])
            for task in simulator_tasks:
                if task.public_id in request.testcase_ids:
                    all_tasks.append((task, simulator["name"].lower()))
        
        await client.close()
        
        if not all_tasks:
            raise HTTPException(status_code=404, detail="No tasks found for the provided testcase_ids")

        # Start background task
        background_tasks.add_task(run_benchmark_background, request)
        
        return {
            "status": "started",
            "message": "Benchmark tasks started in background",
            "testcase_ids": request.testcase_ids,
            "agent": request.agent,
            "version": request.version,
            "runs": request.runs,
            "concurrency": request.concurrency
        }

    except Exception as e:
        logger.error(f"Error starting benchmark: {e}", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "ok"}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
