import logging
import os
from plato.sync_sdk import SyncPlato
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()
BASE_URL = os.getenv("PLATO_BASE_URL")
API_KEY = os.getenv("PLATO_API_KEY")

def main():
    client = SyncPlato(base_url=BASE_URL, api_key=API_KEY)
    running_sessions_count = client.get_running_sessions_count()
    env = client.make_environment(
        "espocrm",
        fast=True,
        interface_type=None,
        # version="latest"
    )
    tasks = client.load_tasks("espocrm")
    task = tasks[0]
    env.wait_for_ready()
    env.reset(task=task)
    public_url = env.get_public_url()
    print(public_url)
    input("Press Enter to continue...")
    # tasks = await client.load_tasks("firefly")
    # task = tasks[0]
    # await env.reset(task=task)
    # breakpoint()
    # state = await env.get_state()
    env.close()

if __name__ == "__main__":
    main()
