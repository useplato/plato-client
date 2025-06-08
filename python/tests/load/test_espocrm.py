import asyncio
import time
from datetime import datetime
from typing import List, Dict
import json
from pathlib import Path

from playwright.async_api import async_playwright
from plato.models import PlatoTask
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

async def run_single_espocrm_test(test_id: int) -> TestMetrics:
    """Run a single EspoCRM login test with metrics tracking."""
    metrics = TestMetrics()
    
    try:
        # Initialize the client
        step_start = time.time()
        client = Plato(base_url="https://plato.so/api")
        
        # Create and initialize the EspoCRM environment
        env = await client.make_environment("espocrm")
        metrics.add_step_timing("environment_creation", time.time() - step_start)
        metrics.set_environment_id(env.id)
        print(f"Test {test_id}: Environment ID: {env.id}")
        
        try:
            # Wait for the environment to be ready
            step_start = time.time()
            print(f"Test {test_id}: Waiting for environment to be ready...")
            await env.wait_for_ready(timeout=300.0)
            metrics.add_step_timing("environment_ready", time.time() - step_start)
            print(f"Test {test_id}: Environment ready")
            
            # Reset the environment
            step_start = time.time()
            await env.reset()
            metrics.add_step_timing("environment_reset", time.time() - step_start)
            print(f"Test {test_id}: Environment reset")
            
            # Get the CDP URL for browser connection
            step_start = time.time()
            print(f"Test {test_id}: Getting CDP URL...")
            cdp_url = await env.get_cdp_url()
            metrics.add_step_timing("get_cdp_url", time.time() - step_start)
            
            # Get live view URL
            live_url = await client.get_live_view_url(env.id)
            print(f"Test {test_id}: Live view URL: {live_url}")
            
            # Connect to browser and perform login
            step_start = time.time()
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                context = browser.contexts[0]
                page = context.pages[0]
                print(f"Test {test_id}: Connected to browser")
                
                # Navigate to EspoCRM.com
                print(f"Test {test_id}: Navigating to espocrm.com...")
                await page.goto("http://espocrm.com/")
                await page.wait_for_timeout(3000)
                
                # Take screenshot after navigation
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_homepage.png"))
                print(f"Test {test_id}: Homepage screenshot taken")
                
                # Fill in username and password
                print(f"Test {test_id}: Filling in credentials...")
                await page.fill('input#field-userName', 'admin')
                await page.fill('input#field-password', 'password')
                
                # Take screenshot before submitting
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_before_submit.png"))
                
                # Click the login button (assuming it's within the div with data-name="submit")
                print(f"Test {test_id}: Clicking submit button...")
                await page.click('[data-name="submit"] button, [data-name="submit"] input[type="submit"]')
                
                # Wait for login to process
                await page.wait_for_timeout(3000)
                print(f"Test {test_id}: Login submitted")
                
                # Take screenshot after login attempt
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_after_login_attempt.png"))
                print(f"Test {test_id}: Login attempt completed")
                
                # Get final state
                state = await env.get_state()
                print(f"Test {test_id}: Final state: {state}")
                
                # Wait a bit to observe the result
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(SCREENSHOTS_DIR / f"test_{test_id}_final_state.png"))
                print(f"Test {test_id}: Final screenshot taken")
            
            metrics.add_step_timing("browser_operations", time.time() - step_start)
            metrics.complete(success=True)
            
        finally:
            # Always ensure we close the environment
            step_start = time.time()
            await env.close()
            metrics.add_step_timing("environment_closure", time.time() - step_start)
            print(f"Test {test_id}: Environment closed")
            
            # Close the client to cleanup aiohttp session
            await client.close()
            print(f"Test {test_id}: Client closed")
            
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
    
    # Run tests in batches
    for batch_start in range(0, total_tests, num_concurrent):
        batch_size = min(num_concurrent, total_tests - batch_start)
        batch_tasks = [
            run_single_espocrm_test(test_id)
            for test_id in range(batch_start, batch_start + batch_size)
        ]
        
        print(f"Starting batch of {batch_size} tests (tests {batch_start} to {batch_start + batch_size - 1})...")
        batch_results = await asyncio.gather(*batch_tasks)
        all_metrics.extend([m.to_dict() for m in batch_results])
        
        # Brief pause between batches to avoid overwhelming the system
        if batch_start + batch_size < total_tests:
            print("Pausing between batches...")
            await asyncio.sleep(2)

    # Calculate and save aggregate metrics
    end_time = time.time()
    total_duration = end_time - start_time
    successful_tests = sum(1 for m in all_metrics if m["success"])
    
    # Calculate step-specific metrics
    step_averages = {}
    for step_name in ["environment_creation", "environment_ready", "environment_reset", 
                      "get_cdp_url", "browser_operations", "environment_closure"]:
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
        print(f"\nStep Performance (Average Duration):")
        for step, times in step_averages.items():
            print(f"  {step}: {times['average']:.2f}s (min: {times['min']:.2f}s, max: {times['max']:.2f}s)")
    
    print(f"\nDetailed metrics saved to: {metrics_file}")
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}")
    print("="*60)

async def test_espocrm_login():
    """Test connecting to EspoCRM environment and logging in to espocrm.com - single test version."""
    metrics = await run_single_espocrm_test(0)
    print(f"\nSingle test completed - Success: {metrics.success}, Duration: {metrics.total_duration:.2f}s")
    if not metrics.success:
        print(f"Error: {metrics.error}")

if __name__ == "__main__":
    # Configure these parameters as needed
    NUM_CONCURRENT_TESTS = 10   # Number of tests to run concurrently
    TOTAL_TESTS = 10           # Total number of tests to run
    RUN_LOAD_TEST = True        # Set to False to run single test instead
    
    if RUN_LOAD_TEST:
        asyncio.run(run_espocrm_load_test(NUM_CONCURRENT_TESTS, TOTAL_TESTS))
    else:
        asyncio.run(test_espocrm_login()) 
