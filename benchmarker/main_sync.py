#!/usr/bin/env python3
"""
Script to create an environment, reset it with a specific task, wait for user input, and evaluate.
"""

from plato.sync_sdk import SyncPlato
from plato.sync_env import SyncPlatoEnvironment


def main():
    # Initialize the Plato client
    client = SyncPlato()

    # 1) Create environment with the specified ID
    env_id = "1fef915b-bc93-4b62-8409-420c49540721"
    print(f"Creating environment with ID: {env_id}")
    env = SyncPlatoEnvironment(client, id=env_id)

    try:
        print("Environment created and ready!")

        # 2) Reset environment with the specified task
        task_public_id = "19fc8dd9-9d07-46b8-9ff4-56901c0696d6"
        task_env_id = "calcom"

        print(f"Loading tasks for environment: {task_env_id}")
        tasks = client.load_tasks(task_env_id)

        # Find the task with the specified public_id
        target_task = None
        for task in tasks:
            if task.public_id == task_public_id:
                target_task = task
                break

        if target_task is None:
            print(f"Task with public_id {task_public_id} not found in {task_env_id} tasks")
            print("Available tasks:")
            for task in tasks:
                print(f"  - {task.public_id}: {task.name}")
            return

        print(f"Resetting environment with task: {target_task.name}\n Prompt: {target_task.prompt}")
        session_id = env.reset(task=target_task)
        print(f"Environment reset complete. Session ID: {session_id}")

        # Print useful URLs
        try:
            public_url = env.get_public_url()
            print(f"Public URL: {public_url}")
        except Exception as e:
            print(f"Could not get live view URL: {e}")


        # 3) Wait for user input
        print("\nEnvironment is ready for interaction.")
        print("Press Enter when you're ready to evaluate the task...")
        input()

        # 4) Run evaluation
        print("Running evaluation...")
        result = env.evaluate()

        print("Evaluation complete!")
        print(f"Success: {result.success}")
        if result.reason:
            print(f"Reason: {result.reason}")
        if hasattr(result, 'diffs') and result.diffs:
            print(f"Diffs: {result.diffs}")

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
