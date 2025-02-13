# Plato Browser Use Example

This example demonstrates how to use the Plato library to run browser-based evaluations.

## Installation

```bash
pip install plato-cli
```

## Using Plato Library

### 1. Getting Test Cases from Dataset

```python
# Fetch test cases using dataset ID
test_cases = await Plato.get_dataset("your_test_case_set_id")
```

### 2. Setting up Runner Configuration

```python
from plato.client import PlatoRunnerConfig

config = PlatoRunnerConfig(
    name="My Test Batch",          # Name for this batch of tests
    data=test_cases,               # Test cases from get_dataset
    task=your_task_function,       # Async function that runs for each test case
    trial_count=1,                 # Number of times to run each test
    timeout=180000,                # Timeout in milliseconds (3 minutes)
    max_concurrency=1              # Number of tests to run in parallel
)
```

### 3. Starting the Run

```python
from plato.client import Plato

# Start the run with your agent version and config
await Plato.start("agent_version_label", config)
```

## Test Case Format

The test cases from the dataset will have this structure:

```json
{
  "name": "Example Test Case",
  "prompt": "What action should be performed?",
  "start_url": "https://example.com",
  "default_scoring_config": {
    "type": "real_eval_scorer",
    "reference_response": "Expected response"
  },
  "config": {
    "challenge_type": "retrieval",
    "difficulty": "easy",
    "website": "example"
  }
}
```

## Complete Example

```python
async def main():
    # Get test cases
    test_cases = await Plato.get_dataset("123")  # Your dataset ID

    # Configure the run
    config = PlatoRunnerConfig(
        name="Browser Test Batch",
        data=test_cases,
        task=your_task_function,
        trial_count=1,
        timeout=180000,
        max_concurrency=1
    )

    # Start the run
    await Plato.start("v1.0.0", config)  # Your agent version

if __name__ == "__main__":
    asyncio.run(main())
```

### Command Line Usage

```bash
python browseruse_example.py --test-case-set-id YOUR_TEST_SET_ID --agent-version YOUR_AGENT_VERSION --batch-name "My Test Batch"
```

#### Arguments
- `--test-case-set-id` (required): The ID of the test case set to run
- `--agent-version` (required): Version label of the agent you are testing
- `--batch-name` (optional): Name for the batch run (defaults to "Test Batch")

## Configuration

The example uses the following default configuration:
- Timeout: 3 minutes per test case
- Concurrency: 1 (runs one test at a time)
- Trial count: 1 per test case

You can modify these settings in the `PlatoRunnerConfig` within the script. 
