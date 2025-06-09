import asyncio
import time
from datetime import datetime
from typing import List, Dict
import json
import os
from pathlib import Path
import aiohttp

from playwright.async_api import async_playwright
from plato.models import PlatoTask
from plato.sdk import Plato

from dotenv import load_dotenv

load_dotenv('.env')

# Create necessary directories at startup
SCREENSHOTS_DIR = Path("screenshots/noop")
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

async def run_single_noop_test(test_id: int) -> TestMetrics:
    """Run a single noop environment test with metrics tracking."""
    metrics = TestMetrics()
    
    try:
        # Initialize the client
        step_start = time.time()
        client = Plato()
        
        # Create and initialize the noop environment
        env = await client.make_environment("espocrm", interface_type=None)
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

            # curl http://espocrm.com with proxy server to PLATO_BASE_URL/proxy/{env.id}
            step_start = time.time()
            
            # Reset the environment
            step_start = time.time()
            await env.reset()
            metrics.add_step_timing("environment_reset", time.time() - step_start)
            print(f"Test {test_id}: Environment reset")
            
            # Perform noop operations (simulate some work)
            step_start = time.time()
            metrics.add_step_timing("noop_operations", time.time() - step_start)
            
            # Test proxy access to espocrm.com using Playwright browser
            step_start = time.time()
            print(f"Test {test_id}: Testing proxy access to espocrm.com with browser...")
            
            # Get the proxy configuration from the environment
            proxy_config = await env.get_proxy_config()
            print(f"Test {test_id}: Proxy config: {proxy_config}")
            
            async with async_playwright() as p:
                try:
                    # Launch browser with proxy configuration
                    browser = await p.chromium.launch(
                        headless=True,
                        proxy=proxy_config
                    )
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    print(f"Test {test_id}: Navigating to espocrm.com through proxy...")
                    await page.goto("http://espocrm.com/", timeout=30000)
                    await page.wait_for_timeout(3000)
                    
                    # Take screenshot
                    screenshot_path = str(SCREENSHOTS_DIR / f"test_{test_id}_espocrm_proxy.png")
                    await page.screenshot(path=screenshot_path)
                    print(f"Test {test_id}: Screenshot saved to {screenshot_path}")
                    
                    # Get page title and URL for verification
                    page_title = await page.title()
                    page_url = page.url
                    
                    await env.log({
                        "message": f"Proxy browser test to espocrm.com completed",
                        "page_title": page_title,
                        "page_url": page_url,
                        "screenshot_path": screenshot_path,
                        "proxy_url": proxy_config
                    }, "info")
                    
                    print(f"Test {test_id}: Page loaded - Title: {page_title}, URL: {page_url}")
                    
                    await browser.close()
                    
                except Exception as proxy_error:
                    print(f"Test {test_id}: Proxy browser test failed: {proxy_error}")
                    await env.log({
                        "message": f"Proxy browser test to espocrm.com failed",
                        "error": str(proxy_error),
                        "proxy_url": proxy_config
                    }, "error")
            
            metrics.add_step_timing("proxy_browser_test", time.time() - step_start)
            
            # Get final state
            step_start = time.time()
            final_state = await env.get_state()
            print(f"Test {test_id}: Final state: {final_state}")
            metrics.add_step_timing("get_final_state", time.time() - step_start)
            
            # Check state mutations
            step_start = time.time()
            mutations = await env.get_state_mutations()
            print(f"Test {test_id}: State mutations: {len(mutations)} mutations detected")
            for i, mutation in enumerate(mutations[:5]):  # Show first 5 mutations
                print(f"Test {test_id}: Mutation {i+1}: {mutation}")
            metrics.add_step_timing("get_mutations", time.time() - step_start)
            
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

async def run_noop_load_test(num_concurrent: int, total_tests: int):
    """
    Run noop load test with specified number of concurrent tests and total test count.
    
    Args:
        num_concurrent (int): Number of tests to run concurrently
        total_tests (int): Total number of tests to run
    """
    all_metrics: List[Dict] = []
    start_time = time.time()

    print(f"Starting noop load test: {total_tests} total tests, {num_concurrent} concurrent")
    
    # Run tests in batches
    for batch_start in range(0, total_tests, num_concurrent):
        batch_size = min(num_concurrent, total_tests - batch_start)
        batch_tasks = [
            run_single_noop_test(test_id)
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
                      "noop_operations", "proxy_browser_test", "get_final_state", "get_mutations", "environment_closure"]:
        step_times = [m["steps_timing"].get(step_name, 0) for m in all_metrics if m["steps_timing"].get(step_name)]
        if step_times:
            step_averages[step_name] = {
                "average": sum(step_times) / len(step_times),
                "min": min(step_times),
                "max": max(step_times)
            }
    
    aggregate_metrics = {
        "test_type": "noop_environment",
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
    metrics_file = METRICS_DIR / f"noop_loadtest_metrics_{timestamp}.json"
    with open(metrics_file, 'w') as f:
        json.dump(aggregate_metrics, f, indent=2)

    print("\n" + "="*60)
    print("NOOP LOAD TEST RESULTS")
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
    print(f"Screenshots directory: {SCREENSHOTS_DIR}")
    print("="*60)

async def test_noop_environment():
    """Test noop environment functionality - single test version."""
    metrics = await run_single_noop_test(0)
    print(f"\nSingle test completed - Success: {metrics.success}, Duration: {metrics.total_duration:.2f}s")
    if not metrics.success:
        print(f"Error: {metrics.error}")

if __name__ == "__main__":
    # Configure these parameters as needed
    NUM_CONCURRENT_TESTS = 1    # Number of tests to run concurrently
    TOTAL_TESTS = 1           # Total number of tests to run
    RUN_LOAD_TEST = True       # Set to False to run single test instead
    
    if RUN_LOAD_TEST:
        asyncio.run(run_noop_load_test(NUM_CONCURRENT_TESTS, TOTAL_TESTS))
    else:
        asyncio.run(test_noop_environment()) 