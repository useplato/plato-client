import asyncio
import time
from datetime import datetime
from typing import List, Dict
import json
from pathlib import Path
from playwright.async_api import async_playwright

from plato.models import PlatoTask
from plato.sdk import Plato

# Create necessary directories at startup
SCREENSHOTS_DIR = Path("screenshots")
METRICS_DIR = Path("metrics")
SCREENSHOTS_DIR.mkdir(exist_ok=True)
METRICS_DIR.mkdir(exist_ok=True)

class TestMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.error = None
        self.steps_timing = {}

    def add_step_timing(self, step_name: str, duration: float):
        self.steps_timing[step_name] = duration

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
            "steps_timing": self.steps_timing,
            "error": self.error
        }

async def run_single_test(test_id: int) -> TestMetrics:
    metrics = TestMetrics()
    start_time = time.time()
    
    try:
        # Initialize the client
        client = Plato(base_url="https://staging.plato.so/api")
        # Create and initialize the environment
        step_start = time.time()
        env = await client.make_environment("espocrm")
        metrics.add_step_timing("environment_creation", time.time() - step_start)

        try:
            # Wait for the environment to be ready
            step_start = time.time()
            await env.wait_for_ready(timeout=300.0)
            metrics.add_step_timing("environment_ready", time.time() - step_start)

            step_start = time.time()
            await env.reset()
            metrics.add_step_timing("environment_reset", time.time() - step_start)

            # Get the CDP URL for browser connection
            step_start = time.time()
            cdp_url = await env.get_cdp_url()
            metrics.add_step_timing("get_cdp_url", time.time() - step_start)

            step_start = time.time()
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                page = await browser.new_page()
                await page.goto("http://espocrm.com/")
                await page.wait_for_timeout(3000)
                
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}.png"))
            
            metrics.add_step_timing("browser_operations", time.time() - step_start)
            metrics.complete(success=True)

        finally:
            # Always ensure we close the environment
            step_start = time.time()
            await env.close()
            metrics.add_step_timing("environment_closure", time.time() - step_start)
            
            # Close the client to cleanup aiohttp session
            await client.close()

    except Exception as e:
        metrics.complete(success=False, error=e)
        print(f"Test {test_id} failed: {str(e)}")
        return metrics

    print(f"Test {test_id} completed successfully")
    return metrics

async def run_load_test(num_concurrent: int, total_tests: int):
    """
    Run load test with specified number of concurrent tests and total test count.
    
    Args:
        num_concurrent (int): Number of tests to run concurrently
        total_tests (int): Total number of tests to run
    """
    all_metrics: List[Dict] = []
    start_time = time.time()

    # Run tests in batches
    for batch_start in range(0, total_tests, num_concurrent):
        batch_size = min(num_concurrent, total_tests - batch_start)
        batch_tasks = [
            run_single_test(test_id)
            for test_id in range(batch_start, batch_start + batch_size)
        ]
        
        print(f"Starting batch of {batch_size} tests...")
        batch_results = await asyncio.gather(*batch_tasks)
        all_metrics.extend([m.to_dict() for m in batch_results])

    # Calculate and save aggregate metrics
    end_time = time.time()
    total_duration = end_time - start_time
    successful_tests = sum(1 for m in all_metrics if m["success"])
    
    aggregate_metrics = {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "failed_tests": total_tests - successful_tests,
        "total_duration": total_duration,
        "tests_per_second": total_tests / total_duration,
        "success_rate": (successful_tests / total_tests) * 100,
        "individual_test_metrics": all_metrics
    }

    # Save metrics to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = METRICS_DIR / f"loadtest_metrics_{timestamp}.json"
    with open(metrics_file, 'w') as f:
        json.dump(aggregate_metrics, f, indent=2)

    print("\nLoad Test Results:")
    print(f"Total Tests: {total_tests}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Failed Tests: {total_tests - successful_tests}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Tests per Second: {total_tests / total_duration:.2f}")
    print(f"Success Rate: {(successful_tests / total_tests) * 100:.2f}%")
    print(f"\nDetailed metrics saved to: {metrics_file}")

if __name__ == "__main__":
    # Configure these parameters as needed
    NUM_CONCURRENT_TESTS = 10  # Number of tests to run concurrently
    TOTAL_TESTS = 10         # Total number of tests to run
    
    asyncio.run(run_load_test(NUM_CONCURRENT_TESTS, TOTAL_TESTS))
