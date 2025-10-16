import logging
import os
import asyncio
from plato.sdk import Plato
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()
BASE_URL = os.getenv("PLATO_BASE_URL")
API_KEY = os.getenv("PLATO_API_KEY")

async def main():
    client = Plato(base_url=BASE_URL, api_key=API_KEY)
    running_sessions_count = await client.get_running_sessions_count()
    env = await client.make_environment(
        "espocrm",
        interface_type=None,
        #tag="prod-latest"
        # dataset="wintergreen",
        #artifact_id="ef95b76e-fe89-479c-bd65-f9710be12f95",
        #artifact_id = "d9ade9e4-73ab-4ba8-8f36-a6535ee9983e",
        artifact_id = "64f92b80-3940-4a7e-9907-e6d6a7954573",
        # version="latest"
    )
    #tasks = await client.load_tasks("espocrm")
    #task = tasks[0]
    await env.wait_for_ready()
    public_url = await env.get_public_url()
    print(public_url)
    await asyncio.sleep(1000)
    input("Press Enter to continue...")
    await env.reset()
    state = await env.get_state()
    print(state)

    input("Press Enter to continue...")
    # tasks = await client.load_tasks("firefly")
    # task = tasks[0]
    # await env.reset(task=task)
    # breakpoint()
    # state = await env.get_state()
    await env.close()
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


