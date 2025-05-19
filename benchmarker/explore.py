#!/usr/bin/env python3

import subprocess
import math
from plato.examples.craigslist_tasks import craigslist_tasks, craigslist_eval_tasks

# Define the list of task objects
TASKS_FOR_EXPLORATION = craigslist_tasks
TASKS_FOR_EVALUATION = craigslist_eval_tasks

M_EVAL_RUNS = 100

for i in range(11):
    N_exploration_runs = 100 * (2 ** i)
    
    print(f"\nITERATION {i+1}/11: Setting N_exploration_runs = {N_exploration_runs}, M_eval_runs = {M_EVAL_RUNS}")
    print("======================================================================")

    # 1. Do N exploration runs on T exploration tasks
    print(f"PHASE 1: EXPLORATION - Running {N_exploration_runs} exploration runs for each of {len(TASKS_FOR_EXPLORATION)} tasks.")
    print("----------------------------------------------------------------------")
    for task_obj in TASKS_FOR_EXPLORATION:
        task_name = task_obj.name
        print(f"  Task: {task_name} (Exploration)")
        
        explore_command = [
            "uv", "run", "main.py",
            "--simulator", "craigslist",
            "--task-name", task_name,
            "--runs", str(N_exploration_runs),
            "--concurrency", "1",
            "--agent", "browser_use",
            "--record-network-requests", "true",
            "--passthrough", "true" # don't need --total-runs for exploration phase since ood requests are not calculated here anyways
        ]
        print(f"    Executing: {' '.join(explore_command)}")
        try:
            subprocess.run(explore_command, check=True, capture_output=True, text=True)
            print(f"    SUCCESS: Exploration for {task_name} with {N_exploration_runs} runs.")
        except subprocess.CalledProcessError as e:
            print(f"    ERROR running exploration for task {task_name}:")
            print(f"    Command: {' '.join(e.cmd)}")
            print(f"    Return code: {e.returncode}")
            print(f"    Stdout: {e.stdout}")
            print(f"    Stderr: {e.stderr}")


    # 2. Run M eval runs on T eval tasks
    # print(f"\nPHASE 2: EVALUATION - Running {M_EVAL_RUNS} eval runs for each of {len(TASKS_FOR_EVALUATION)} eval tasks.")
    print(f"\nPHASE 2: EVALUATION - Running {M_EVAL_RUNS} eval runs for each of {len(TASKS_FOR_EXPLORATION)} exploration tasks.")
    print("----------------------------------------------------------------------")
    # for eval_task_obj in TASKS_FOR_EVALUATION:
    for eval_task_obj in TASKS_FOR_EXPLORATION:
        eval_task_name = eval_task_obj.name
        print(f"  Task: {eval_task_name} (Evaluation)")

        eval_command = [
            "uv", "run", "main.py",
            "--simulator", "craigslist",
            "--task-name", eval_task_name,
            "--runs", str(M_EVAL_RUNS),
            "--concurrency", "1",
            "--agent", "browser_use",
            "--record-network-requests", "true",
            "--passthrough", "false",
            "--total-runs", str(N_exploration_runs) # TODO: hack to get the number of runs done in exploration phase
        ]
        print(f"    Executing: {' '.join(eval_command)}")
        try:
            subprocess.run(eval_command, check=True, capture_output=True, text=True)
            print(f"    SUCCESS: Evaluation for {eval_task_name} with {M_EVAL_RUNS} runs.")
        except subprocess.CalledProcessError as e:
            print(f"    ERROR running evaluation for task {eval_task_name}:")
            print(f"    Command: {' '.join(e.cmd)}")
            print(f"    Return code: {e.returncode}")
            print(f"    Stdout: {e.stdout}")
            print(f"    Stderr: {e.stderr}")

    # 3. Clear S3 cache (N increases automatically in the next iteration of the outer loop)
    print(f"\nPHASE 3: S3 CACHE CLEARING")
    print("----------------------------------------------------------------------")
    print("  IMPORTANT: You need to implement the S3 cache clearing command below.")
    # Example S3 cache clearing command (replace with your actual command):
    # s3_cache_clear_command = ["aws", "s3", "rm", "s3://your-bucket-name/path-to-cache/", "--recursive"]
    # try:
    #     print(f"    Executing: {' '.join(s3_cache_clear_command)}")
    #     subprocess.run(s3_cache_clear_command, check=True)
    #     print("    SUCCESS: S3 cache cleared.")
    # except subprocess.CalledProcessError as e:
    #     print(f"    ERROR clearing S3 cache:")
    #     print(f"    Command: {' '.join(e.cmd)}")
    #     print(f"    Return code: {e.returncode}")
    #     print(f"    Stderr: {e.stderr}")
    # except FileNotFoundError:
    #     print(f"    ERROR: AWS CLI not found. Cannot clear S3 cache.")
    print("  Skipping S3 cache clearing as it's a placeholder.")
    print("======================================================================")

print("\nAll benchmark iterations completed.") 