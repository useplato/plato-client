
## Quick Start

Here's a basic example of how to use the Plato Client SDK:


**Create an enviornment and connect to it using the cdp_url**
```python
import asyncio
import os
from plato import Plato, PlatoTask

base_prompt = """
You are a helpful assistant that can help me buy food from doordash.
start by going to {start_url}. Do not navigate to other websites.
Do not end the task until you have completed and paid for the order.
Here is the task:
{prompt}

Make sure to complete the checkout process once you've added the necessary items to cart.
The task is not complete until the order is sent and paid for.
You do not need my permission to and place an order.
"""

async def run_task(client: Plato, task: PlatoTask):
    env = await client.make_environment(task.env_id, open_page_on_start=False)

    await env.wait_for_ready()
    await env.reset(task)

    cdp_url = await env.get_cdp_url()

    prompt = base_prompt.format(start_url=task.start_url, prompt=task.prompt)

    # live view url to watch live
    live_view_url = await env.get_live_view_url()
    print(f"Live view URL: {live_view_url}")


    try:
        # connect agent and run
        await YourAgent.run(cdp_url, prompt)

        result = await env.evaluate()
        print(f"Evaluation result: {result}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await env.close()


async def main():
    client = Plato(api_key=os.environ.get("PLATO_API_KEY"))
    tasks = await client.load_tasks("doordash")
    for task in doordash_tasks:
        await run_task(client, task)


if __name__ == "__main__":
    asyncio.run(main())

```


## Core Components

### Plato Client
The main entry point for interacting with the Plato platform. Handles authentication and environment management.

```python
client = Plato(base_url="https://plato.so/api", api_key="your_api_key")
```

### PlatoTask
Represents a task to be performed by an AI agent. Contains the task description, starting URL, and environment configuration.

```python
class PlatoTask:
    name: str # ex: order_medium_cheese_pizza
    prompt: str # ex: Order a medium cheese pizza from the nearest papa john's
    start_url: str # ex: https://www.doordash.com
    env_id: str # ex: doordash

```

### PlatoEnvironment
Manages the browser environment for task execution. Provides methods for controlling the browser and evaluating task completion.

```python
env = await client.make_environment(task.env_id)
await env.reset(task, agent_version="agent_version")
```

## Examples

For complete examples of using the SDK with different AI models (OpenAI, Anthropic, Browser Use), check out the [examples directory](examples/README.md). The examples demonstrate:

- Running tasks with different AI agents
- Setting up environments
- Task evaluation
- Live monitoring
- Concurrent task execution

### Available Task Sets
- DoorDash automation
- EspoCRM tasks
- Roundcube webmail
- Mattermost collaboration

## Environment Variables

Required environment variables:
- `PLATO_API_KEY`: Your Plato API key
- `OPENAI_API_KEY`: Required for OpenAI agent
- `ANTHROPIC_API_KEY`: Required for Anthropic agent

## License

[License information to be added]
