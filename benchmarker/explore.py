#!/usr/bin/env python3

import subprocess
import requests
import asyncio
from plato.examples.craigslist_tasks import craigslist_tasks, craigslist_eval_tasks
from main import main

# Define the list of task objects
# TASKS_FOR_EXPLORATION = craigslist_tasks
# TASKS_FOR_EVALUATION = craigslist_eval_tasks

TASKS_FOR_EXPLORATION = [craigslist_tasks[0]]
TASKS_FOR_EVALUATION = [craigslist_tasks[0]]

M_EVAL_RUNS = 100

CONCURRENCY = 5
SIMULATOR_NAME = "craigslist"

async def explore():
    for i in range(11):
        N_exploration_runs = 100 * (2 ** i)

        exploration_session_ids = []
        
        print(f"\nITERATION {i+1}/11: Setting N_exploration_runs = {N_exploration_runs}, M_eval_runs = {M_EVAL_RUNS}")
        print("======================================================================")

        # 1. Do N exploration runs on T exploration tasks
        print(f"PHASE 1: EXPLORATION - Running {N_exploration_runs} exploration runs for each of {len(TASKS_FOR_EXPLORATION)} tasks.")
        print("----------------------------------------------------------------------")
        for task_obj in TASKS_FOR_EXPLORATION:
            task_name = task_obj.name
            print(f"  Task: {task_name} (Exploration)")
            
            try:
                exploration_session_ids += await main(
                    simulator=SIMULATOR_NAME,
                    task_name=task_name,
                    runs=N_exploration_runs,
                    concurrency=CONCURRENCY,
                    agent="browser_use",
                    record_network_requests="true",
                    passthrough="true" # don't need --total-runs for exploration phase since ood requests are not calculated here anyways
                )
                print(f"    SUCCESS: Exploration for {task_name} with {N_exploration_runs} runs.")
            except subprocess.CalledProcessError as e:
                print(f"    ERROR running exploration for task {task_name}:")
                print(f"    Command: {' '.join(e.cmd)}")
                print(f"    Return code: {e.returncode}")
                print(f"    Stdout: {e.stdout}")
                print(f"    Stderr: {e.stderr}")


        # 2. Run M eval runs on T eval tasks
        print(f"\nPHASE 2: EVALUATION - Running {M_EVAL_RUNS} eval runs for each of {len(TASKS_FOR_EVALUATION)} eval tasks.")
        print("----------------------------------------------------------------------")

        # before running the eval runs, set cached sessions to cached sessions from the exploration runs
        print("    Executing: PUT request to set simulator cached sessions")
        response = requests.put(
            f"http://localhost:8000/simulator/cached_sessions/{SIMULATOR_NAME}",
            json={"session_ids": exploration_session_ids},
            headers={"Content-Type": "application/json"}
        )

        for eval_task_obj in TASKS_FOR_EVALUATION:
            eval_task_name = eval_task_obj.name
            print(f"  Task: {eval_task_name} (Evaluation)")

            try:
                await main(
                    simulator=SIMULATOR_NAME,
                    task_name=eval_task_name,
                    runs=M_EVAL_RUNS,
                    concurrency=CONCURRENCY,
                    agent="browser_use",
                    record_network_requests="true",
                    passthrough="false",
                    total_runs=N_exploration_runs
                )
                print(f"    SUCCESS: Evaluation for {eval_task_name} with {M_EVAL_RUNS} runs.")
            except subprocess.CalledProcessError as e:
                print(f"    ERROR running evaluation for task {eval_task_name}:")
                print(f"    Command: {' '.join(e.cmd)}")
                print(f"    Return code: {e.returncode}")
                print(f"    Stdout: {e.stdout}")
                print(f"    Stderr: {e.stderr}")

        # 3. Clear cache (N increases automatically in the next iteration of the outer loop)
        print(f"\nPHASE 3: CACHE CLEARING")
        print("----------------------------------------------------------------------")
        try:
            print("    Executing: PUT request to clear simulator cached sessions")
            response = requests.put(
                f"http://localhost:8000/simulator/cached_sessions/{SIMULATOR_NAME}",
                json={"session_ids": []},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            print("    SUCCESS: Simulator cached sessions cleared.")
        except subprocess.CalledProcessError as e:
            print(f"    ERROR clearing simulator cached sessions:")
            print(f"    Command: {' '.join(e.cmd)}")
            print(f"    Return code: {e.returncode}")
            print(f"    Stdout: {e.stdout}")
            print(f"    Stderr: {e.stderr}")

        print("  Skipping cache clearing as it's a placeholder.")
        print("======================================================================")

    print("\nAll benchmark iterations completed.") 


if __name__ == "__main__":
    asyncio.run(explore())