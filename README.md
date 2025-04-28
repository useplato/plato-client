# Plato Client SDK

A Python SDK for building and testing AI agents on web automation tasks. This SDK provides a framework for creating, testing, and evaluating AI agents across different web platforms.

## Installation

1. Clone the repository
2. Install dependencies:
```bash
uv sync
```

## Quick Start

Here's a basic example of how to use the Plato Client SDK:

```python
from plato import Plato, PlatoTask
from plato.models.env import PlatoEnvironment

# Initialize the Plato client
client = Plato(base_url="https://plato.so/api", api_key="your_api_key")

# Create a task
task = PlatoTask(
    name="example_task",
    prompt="Your task description here",
    start_url="https://example.com",
    env_id="your_env_id"
)

# Create an environment
env = await client.make_environment(task.env_id)

# Run the task
await env.reset(task, agent_version="your_agent_version")
cdp_url = await env.get_cdp_url()

# Get live view URL for monitoring
live_view_url = await env.get_live_view_url()

# Run your agent here using the cdp_url

# Evaluate the task
eval_result = await env.evaluate()

# Clean up
await env.close()
await client.close()
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
task = PlatoTask(
    name="task_name",
    prompt="Task description",
    start_url="https://example.com",
    env_id="env_id"
)
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