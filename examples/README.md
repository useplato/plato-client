# Plato Client

A benchmarking tool for testing AI agents on web automation tasks across different platforms and scenarios.

## Overview

This tool allows you to run automated tests using different AI agents (Browser Use, Anthropic, OpenAI) across various web platforms including:
- DoorDash
- EspoCRM
- Roundcube
- Mattermost

## Prerequisites

- Python 3.x
- Environment variables:
  - `PLATO_API_KEY`
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY` (if using Anthropic agent)

## Installation

1. Clone the repository
2. Create a `.env` file with the required environment variables
3. Install dependencies:
```bash
uv sync
```

## Usage

Run the benchmark using the following command:

```bash
uv run main.py --task-set <task_set> [options]
```

### Live View

When running tasks, a live view URL will be displayed in the console output. This URL allows you to observe the agent's actions in real-time through a web interface. The live view shows:
- The browser window being controlled by the agent
- Real-time actions and interactions
- Task progress and status

This is particularly useful for:
- Debugging agent behavior
- Understanding how the agent approaches different tasks
- Monitoring long-running tasks
- Verifying task completion

### Command Line Arguments

- `--task-set`: Required. Choose from: doordash, espocrm, roundcube, mattermost
- `--task-name`: Optional. Run a specific task by name
- `--list-tasks`: Optional. List all available tasks in the specified task set
- `--runs`: Optional. Number of runs per task (default: 1)
- `--concurrency`: Optional. Number of concurrent tasks (default: 5)
- `--agent`: Optional. Choose agent type:
  - browser_use (default)
  - anthropic
  - openai_cua
- `--tag`: Optional. Tag for agent version (e.g., '20250423')

### Examples

List all available tasks in the EspoCRM task set:
```bash
uv run main.py --task-set espocrm --list-tasks
```

Run a specific DoorDash task with 3 concurrent runs:
```bash
uv run main.py --task-set doordash --task-name "your_task_name" --runs 3
```

Run all Roundcube tasks using the Anthropic agent:
```bash
uv run main.py --task-set roundcube --agent anthropic
```

## Task Sets

### DoorDash
- Simulates food ordering process
- Can add items to cart and view total price
- Requires user permission for checkout
- [View DoorDash Tasks](python/src/plato/examples/doordash_tasks.py)

### EspoCRM
- CRM system automation
- Default credentials:
  - Username: admin
  - Password: password
- [View EspoCRM Tasks](python/src/plato/examples/espocrm_tasks.py)

### Roundcube
- Webmail system automation
- Default credentials:
  - Username: sarah.chen@technova.io
  - Password: password
- [View Roundcube Tasks](python/src/plato/examples/roundcube_tasks.py)

### Mattermost
- Team collaboration platform automation
- Default credentials:
  - Username: alex.reynolds
  - Password: password
- [View Mattermost Tasks](python/src/plato/examples/mattermost_tasks.py)

## License

[License information to be added]

