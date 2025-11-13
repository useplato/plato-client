from plato import Plato
from plato.models.env import PlatoEnvironment
import asyncio

client = Plato()

async def main():
    tasks = await client.load_tasks("espocrm")
    print(len(tasks))
    env = await client.make_environment("espocrm")
    await env.wait_for_ready()
    print(env.id)
    await env.reset(task=tasks[1])
    await env.evaluate()

    # reconstruct a new env
    print("reconstructing env")
    env = await PlatoEnvironment.from_id(client, env.id)
    await env.evaluate()

if __name__ == "__main__":
    asyncio.run(main())