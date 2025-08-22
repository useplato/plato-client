import logging
import os
from plato.sdk import Plato
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()
BASE_URL = os.getenv("PLATO_BASE_URL")
API_KEY = os.getenv("PLATO_API_KEY")

async def main():
    breakpoint()
    client = Plato(base_url=BASE_URL, api_key=API_KEY)
    running_sessions_count = await client.get_running_sessions_count()
    breakpoint()
    env = await client.make_environment(
        "snipeit",
        fast=True,
        interface_type=None
    )
    breakpoint()
    await env.wait_for_ready()
    tasks = await client.load_tasks("snipeit")
    task = tasks[0]
    await env.reset(task=task)
    breakpoint()
    state = await env.get_state()
    await env.close()
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
