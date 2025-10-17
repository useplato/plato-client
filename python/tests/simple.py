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
    client = Plato(base_url=BASE_URL, api_key=API_KEY)
    running_sessions_count = await client.get_running_sessions_count()
    # tasks = await client.load_tasks("espocrm")
    # task = next(task for task in tasks if task.public_id == "8bdbccdc-fe4e-4487-b7ef-96167d1bb609")
    env = await client.make_environment(
        "espocrm",
        fast=True,
        record_network_requests=True,
        interface_type=None,
        # dataset="wintergreen",
        # artifact_id="0783da5f-cf62-49aa-98d1-bffdcf63f311",
        # artifact_id="56f85a14-8e82-4053-a7df-8490c31a14e3",
        # artifact_id=task.simulator_artifact_id,
        # version="latest"
    )
    await env.wait_for_ready()
    # await env.reset(task=task)
    await env.reset()
    public_url = await env.get_public_url()
    print(public_url)
    input("Press Enter to continue...")

    # mutations = await env.get_state_mutations()
    # print(mutations)

    # await env.evaluate({"test": True })
    await env.evaluate()

    # tasks = await client.load_tasks("firefly")
    # task = tasks[0]
    # await env.reset(task=task)
    # breakpoint()
    # state = await env.get_state()
    await env.close()

    # Example of creating PlatoTaskMetadata with sample values
    from plato.models.task import PlatoTaskMetadata

    metadata_config = PlatoTaskMetadata(
        goal_type=None,
        reasoning_level="level_2",
        skills=[
            "go_to_url",
            "click",
            "text_input",
            "dropdown_selection",
            "scroll",
            "form_submit",
            "read_visible_text"
        ],
        capabilities=[
            "tabs_nav",
            "notification_banner"
        ],
        tags=[
            "form-fill-oct8"
        ],
        rejected=True
    )

    print("Metadata config:", metadata_config.model_dump())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


