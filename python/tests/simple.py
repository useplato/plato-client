import logging
import os
import time
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
        "mattermost",
        interface_type=None,
	#tag='amazon-latest',
        # dataset="wintergreen",
        #artifact_id="8e5b0d52-b312-4849-abe1-15aed8ef3f72",
        # version="latest"
    )
    print(env.id)
    #tasks = await client.load_tasks("espocrm")
    #task = tasks[0]
    start = time.time()
    await env.wait_for_ready()
    end = time.time()
    print(end - start)
    public_url = await env.get_public_url()
    print(public_url)

    breakpoint()
    await env.reset()
    await asyncio.sleep(100)
    input("Press Enter to continue...")

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


