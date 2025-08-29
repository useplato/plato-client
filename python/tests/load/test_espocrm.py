import asyncio
import time
from datetime import datetime
from typing import List, Dict
import json
from pathlib import Path

from playwright.async_api import async_playwright
from plato.sdk import Plato

from dotenv import load_dotenv

load_dotenv('.env')

# Create necessary directories at startup
SCREENSHOTS_DIR = Path("screenshots/espocrm")
METRICS_DIR = Path("metrics")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(exist_ok=True)

class TestMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.error = None
        self.environment_id = None
        self.steps_timing = {}

    def add_step_timing(self, step_name: str, duration: float):
        self.steps_timing[step_name] = duration

    def set_environment_id(self, env_id: str):
        self.environment_id = env_id

    def complete(self, success: bool, error=None):
        self.end_time = time.time()
        self.success = success
        self.error = str(error) if error else None

    @property
    def total_duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "total_duration": self.total_duration,
            "environment_id": self.environment_id,
            "steps_timing": self.steps_timing,
            "error": self.error
        }

async def run_single_espocrm_test(test_id: int, client: Plato, tasks: List) -> TestMetrics:
    """Run a single EspoCRM login test with metrics tracking."""
    metrics = TestMetrics()

    try:
        # Create and initialize the EspoCRM environment
        step_start = time.time()
        env = await client.make_environment("espocrm", open_page_on_start=True, interface_type=None)
        metrics.add_step_timing("environment_creation", time.time() - step_start)
        metrics.set_environment_id(env.id)
        print(f"Test {test_id}: Environment ID: {env.id}")

        try:
            # Wait for the environment to be ready
            step_start = time.time()
            print(f"Test {test_id}: Waiting for environment to be ready...")
            await env.wait_for_ready()
            metrics.add_step_timing("environment_ready", time.time() - step_start)
            print(f"Test {test_id}: Environment ready")

            # Perform the complete workflow 3 times (reset + browser operations)
            workflow_times = []
            for iteration in range(3):
                iteration_start = time.time()
                print(f"\nTest {test_id}: Starting iteration #{iteration + 1}")

                # Reset the environment
                reset_start = time.time()
                await env.reset(task=tasks[0])
                reset_duration = time.time() - reset_start
                print(f"Test {test_id}: Environment reset #{iteration + 1} completed in {reset_duration:.2f}s")

                # Get the public URL for browser navigation
                public_url_start = time.time()
                print(f"Test {test_id}: Getting public URL...")
                public_url = await env.get_public_url()
                public_url_duration = time.time() - public_url_start
                metrics.add_step_timing("public_url_retrieval", public_url_duration)

                # Connect to browser and perform login
                browser_start = time.time()
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()
                    print(f"Test {test_id}: Created new headless browser for iteration #{iteration + 1}")

                    # Navigate to the public URL
                    print(f"Test {test_id}: Navigating to public URL: {public_url}")
                    await page.goto(public_url)
                    print(f"Test {test_id}: Successfully navigated to public URL")

                    # Take screenshot after navigation
                    await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_iteration_{iteration + 1}_homepage.png"))
                    print(f"Test {test_id}: Homepage screenshot taken for iteration #{iteration + 1}")

                    # Fill in username and password
                    print(f"Test {test_id}: Filling in credentials...")
                    await page.fill('input#field-userName', 'admin')
                    await page.fill('input#field-password', 'password')

                    # Take screenshot before submitting
                    await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_iteration_{iteration + 1}_before_submit.png"))

                    # Click the login button
                    print(f"Test {test_id}: Clicking submit button...")
                    await page.click('[data-name="submit"] button, [data-name="submit"] input[type="submit"]')

                    # Wait for login to process
                    await page.wait_for_timeout(3000)
                    print(f"Test {test_id}: Login submitted for iteration #{iteration + 1}")

                    # Take screenshot after login attempt
                    await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_iteration_{iteration + 1}_after_login.png"))
                    print(f"Test {test_id}: Login attempt completed for iteration #{iteration + 1}")

                    # Get final state
                    state = await env.get_state()
                    print(f"Test {test_id}: Final state for iteration #{iteration + 1}: {state}")

                    # Wait a bit to observe the result
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_iteration_{iteration + 1}_final.png"))
                    print(f"Test {test_id}: Final screenshot taken for iteration #{iteration + 1}")

                    # Close the browser
                    await browser.close()
                    print(f"Test {test_id}: Browser closed for iteration #{iteration + 1}")

                browser_duration = time.time() - browser_start
                iteration_duration = time.time() - iteration_start
                workflow_times.append(iteration_duration)

                print(f"Test {test_id}: Iteration #{iteration + 1} completed in {iteration_duration:.2f}s")

                # Brief pause between iterations
                if iteration < 2:  # Don't wait after the last iteration
                    await asyncio.sleep(1)

            # Record aggregate timing metrics
            total_workflow_time = sum(workflow_times)
            metrics.add_step_timing("total_workflow_iterations", total_workflow_time)
            metrics.add_step_timing("average_iteration_time", total_workflow_time / 3)
            print(f"Test {test_id}: All 3 iterations completed in {total_workflow_time:.2f}s (avg: {total_workflow_time / 3:.2f}s)")

            metrics.complete(success=True)

        finally:
            # Always ensure we close the environment
            step_start = time.time()
            await env.close()
            metrics.add_step_timing("environment_closure", time.time() - step_start)
            print(f"Test {test_id}: Environment closed")

    except Exception as e:
        metrics.complete(success=False, error=e)
        print(f"Test {test_id} failed with error: {e}")
        return metrics

    print(f"Test {test_id} completed successfully")
    return metrics

async def run_espocrm_load_test(num_concurrent: int, total_tests: int):
    """
    Run EspoCRM load test with specified number of concurrent tests and total test count.

    Args:
        num_concurrent (int): Number of tests to run concurrently
        total_tests (int): Total number of tests to run
    """
    all_metrics: List[Dict] = []
    start_time = time.time()

    print(f"Starting EspoCRM load test: {total_tests} total tests, {num_concurrent} concurrent")

    # Initialize the client and load tasks once
    print("Initializing client and loading tasks...")
    client = Plato(base_url="https://plato.so/api")
    tasks = await client.load_tasks("espocrm")
    print(f"Loaded {len(tasks)} tasks")

    try:
        # Run tests in batches
        for batch_start in range(0, total_tests, num_concurrent):
            batch_size = min(num_concurrent, total_tests - batch_start)
            batch_tasks = [
                run_single_espocrm_test(test_id, client, tasks)
                for test_id in range(batch_start, batch_start + batch_size)
            ]

            print(f"Starting batch of {batch_size} tests (tests {batch_start} to {batch_start + batch_size - 1})...")
            batch_results = await asyncio.gather(*batch_tasks)
            all_metrics.extend([m.to_dict() for m in batch_results])

            # Brief pause between batches to avoid overwhelming the system
            if batch_start + batch_size < total_tests:
                print("Pausing between batches...")
                await asyncio.sleep(2)

    finally:
        # Always ensure we close the client to cleanup aiohttp session
        await client.close()
        print("Client closed")

    # Calculate and save aggregate metrics
    end_time = time.time()
    total_duration = end_time - start_time
    successful_tests = sum(1 for m in all_metrics if m["success"])

    # Calculate step-specific metrics
    step_averages = {}
    for step_name in ["environment_creation", "environment_ready", "total_workflow_iterations",
                      "average_iteration_time", "environment_closure", "public_url_retrieval"]:
        step_times = [m["steps_timing"].get(step_name, 0) for m in all_metrics if m["steps_timing"].get(step_name)]
        if step_times:
            step_averages[step_name] = {
                "average": sum(step_times) / len(step_times),
                "min": min(step_times),
                "max": max(step_times)
            }

    aggregate_metrics = {
        "test_type": "espocrm_login",
        "total_tests": total_tests,
        "concurrent_tests": num_concurrent,
        "successful_tests": successful_tests,
        "failed_tests": total_tests - successful_tests,
        "total_duration": total_duration,
        "tests_per_second": total_tests / total_duration,
        "success_rate": (successful_tests / total_tests) * 100,
        "step_averages": step_averages,
        "individual_test_metrics": all_metrics
    }

    # Save metrics to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = METRICS_DIR / f"espocrm_loadtest_metrics_{timestamp}.json"
    with open(metrics_file, 'w') as f:
        json.dump(aggregate_metrics, f, indent=2)

    print("\n" + "="*60)
    print("ESPOCRM LOAD TEST RESULTS")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Concurrent Tests: {num_concurrent}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Failed Tests: {total_tests - successful_tests}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Tests per Second: {total_tests / total_duration:.2f}")
    print(f"Success Rate: {(successful_tests / total_tests) * 100:.2f}%")

    if step_averages:
        print("\nStep Performance (Average Duration):")
        for step, times in step_averages.items():
            print(f"  {step}: {times['average']:.2f}s (min: {times['min']:.2f}s, max: {times['max']:.2f}s)")

    print(f"\nDetailed metrics saved to: {metrics_file}")
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}")
    print("="*60)

async def test_espocrm_login():
    """Test connecting to EspoCRM environment and logging in to espocrm.com - single test version."""
    # Initialize the client and load tasks once
    client = Plato(base_url="https://plato.so/api")
    tasks = await client.load_tasks("espocrm")

    try:
        metrics = await run_single_espocrm_test(0, client, tasks)
        print(f"\nSingle test completed - Success: {metrics.success}, Duration: {metrics.total_duration:.2f}s")
        if not metrics.success:
            print(f"Error: {metrics.error}")
    finally:
        await client.close()

if __name__ == "__main__":
    # Configure these parameters as needed
    NUM_CONCURRENT_TESTS = 500   # Number of tests to run concurrently
    TOTAL_TESTS = 500          # Total number of tests to run
    RUN_LOAD_TEST = True        # Set to False to run single test instead

    if RUN_LOAD_TEST:
        asyncio.run(run_espocrm_load_test(NUM_CONCURRENT_TESTS, TOTAL_TESTS))
    else:
        asyncio.run(test_espocrm_login())
