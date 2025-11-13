import asyncio
import time
import argparse
from datetime import datetime
from typing import List, Dict, Optional
import json
from pathlib import Path

from playwright.async_api import async_playwright
from plato.models import PlatoTask
from plato.sdk import Plato

from dotenv import load_dotenv

load_dotenv('.env')

class TestMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.error = None
        self.environment_id = None
        self.environment_name = None
        self.steps_timing = {}

    def add_step_timing(self, step_name: str, duration: float):
        self.steps_timing[step_name] = duration

    def set_environment_info(self, env_id: str, env_name: str):
        self.environment_id = env_id
        self.environment_name = env_name

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
            "environment_name": self.environment_name,
            "steps_timing": self.steps_timing,
            "error": self.error
        }

async def run_environment_test(
    env_name: str, 
    take_screenshots: bool = True, 
    task_index: int = 0,
    record_actions: bool = False,
    wait_for_user: bool = True
) -> TestMetrics:
    """Run a test on the specified environment with metrics tracking."""
    metrics = TestMetrics()
    
    # Create screenshots directory
    screenshots_dir = Path(f"screenshots/{env_name}")
    if take_screenshots:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize the client
        step_start = time.time()
        client = Plato()
        
        # Load tasks for the environment
        try:
            tasks = await client.load_tasks(env_name)
            if not tasks:
                raise ValueError(f"No tasks found for environment '{env_name}'")
            
            # Use specified task index or first task
            if task_index >= len(tasks):
                print(f"Warning: Task index {task_index} out of range, using first task")
                task_index = 0
            
            selected_task = tasks[task_index]
            print(f"Selected task: {selected_task.name}")
            
        except Exception as e:
            print(f"Warning: Could not load tasks for '{env_name}': {e}")
            print("Continuing without a specific task...")
            tasks = []
            selected_task = None
        
        # Create the environment
        env = await client.make_environment(
            env_name, 
            open_page_on_start=True,
            record_actions=record_actions
        )
        metrics.add_step_timing("environment_creation", time.time() - step_start)
        metrics.set_environment_info(env.id, env_name)
        print(f"Environment ID: {env.id}")
        
        try:
            # Wait for the environment to be ready
            step_start = time.time()
            print("Waiting for environment to be ready...")
            await env.wait_for_ready(timeout=300.0)
            metrics.add_step_timing("environment_ready", time.time() - step_start)
            print("Environment ready")
            
            # Reset with task if available
            if selected_task:
                reset_start = time.time()
                print(f"Resetting environment with task: {selected_task.name}")
                await env.reset(task=selected_task)
                reset_duration = time.time() - reset_start
                metrics.add_step_timing("environment_reset", reset_duration)
                print(f"Environment reset completed in {reset_duration:.2f}s")
            
            # Get CDP URL and live view URL
            cdp_start = time.time()
            print("Getting CDP URL...")
            cdp_url = await env.get_cdp_url()
            cdp_duration = time.time() - cdp_start
            metrics.add_step_timing("cdp_connection", cdp_duration)
            
            live_url = await client.get_live_view_url(env.id)
            print(f"Live view URL: {live_url}")
            
            # Connect to browser
            browser_start = time.time()
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                context = browser.contexts[0]
                page = context.pages[0]
                print("Connected to browser")
                
                # Take initial screenshot
                if take_screenshots:
                    await page.screenshot(path=str(screenshots_dir / f"initial_state.png"))
                    print("Initial screenshot taken")
                
                # Get page title and URL
                title = await page.title()
                url = page.url
                print(f"Page title: {title}")
                print(f"Page URL: {url}")
                
                # Wait and take another screenshot
                await page.wait_for_timeout(3000)
                if take_screenshots:
                    await page.screenshot(path=str(screenshots_dir / f"after_wait.png"))
                    print("Screenshot after wait taken")
                
                # Get environment state
                state = await env.get_state()
                print(f"Environment state: {state}")
                
                # Take final screenshot
                if take_screenshots:
                    await page.screenshot(path=str(screenshots_dir / f"final_state.png"))
                    print("Final screenshot taken")
            
            browser_duration = time.time() - browser_start
            metrics.add_step_timing("browser_interaction", browser_duration)
            
            # Wait for user interaction before closing (if enabled)
            if wait_for_user:
                print(f"\n{'='*60}")
                print("ENVIRONMENT IS READY FOR INTERACTION")
                print(f"{'='*60}")
                print(f"Environment ID: {env.id}")
                print(f"Live view URL: {live_url}")
                print("The environment is now ready for manual interaction.")
                print("You can use the live view URL to interact with the environment.")
                print(f"{'='*60}")
                input("Press ENTER when you're done interacting with the environment to close it...")
                print("Closing environment...")
            else:
                print("Skipping user interaction wait...")
            
            metrics.complete(success=True)
            
        finally:
            # Always ensure we close the environment
            step_start = time.time()
            await env.close()
            metrics.add_step_timing("environment_closure", time.time() - step_start)
            print("Environment closed")
            
            # Close the client to cleanup aiohttp session
            await client.close()
            print("Client closed")
            
    except Exception as e:
        metrics.complete(success=False, error=e)
        print(f"Test failed with error: {e}")
        return metrics

    print("Test completed successfully")
    return metrics

async def list_available_environments():
    """List all available environments."""
    try:
        client = Plato()
        simulators = await client.list_simulators()
        await client.close()
        
        print("Available environments:")
        for sim in simulators:
            print(f"  - {sim['name']}: {sim.get('description', 'No description')}")
        
        return [sim['name'] for sim in simulators]
    except Exception as e:
        print(f"Error listing environments: {e}")
        return []

async def main():
    parser = argparse.ArgumentParser(description='Test a Plato environment')
    parser.add_argument('environment', nargs='?', help='Environment name to test')
    parser.add_argument('--list', action='store_true', help='List available environments')
    parser.add_argument('--no-screenshots', action='store_true', help='Disable taking screenshots')
    parser.add_argument('--task-index', type=int, default=0, help='Index of task to use (default: 0)')
    parser.add_argument('--record-actions', action='store_true', help='Enable action recording')
    parser.add_argument('--save-metrics', action='store_true', help='Save metrics to file')
    parser.add_argument('--no-wait', action='store_true', help='Skip waiting for user interaction before closing')
    
    args = parser.parse_args()
    
    if args.list:
        await list_available_environments()
        return
    
    if not args.environment:
        print("Error: Environment name is required")
        print("Use --list to see available environments")
        parser.print_help()
        return
    
    print(f"Testing environment: {args.environment}")
    print(f"Screenshots: {'disabled' if args.no_screenshots else 'enabled'}")
    print(f"Task index: {args.task_index}")
    print(f"Record actions: {'enabled' if args.record_actions else 'disabled'}")
    print(f"Wait for user: {'disabled' if args.no_wait else 'enabled'}")
    
    # Run the test
    metrics = await run_environment_test(
        env_name=args.environment,
        take_screenshots=not args.no_screenshots,
        task_index=args.task_index,
        record_actions=args.record_actions,
        wait_for_user=not args.no_wait
    )
    
    # Print results
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    print(f"Environment: {metrics.environment_name}")
    print(f"Environment ID: {metrics.environment_id}")
    print(f"Success: {'✓' if metrics.success else '✗'}")
    print(f"Total Duration: {metrics.total_duration:.2f} seconds")
    
    if metrics.steps_timing:
        print(f"\nStep Timings:")
        for step, duration in metrics.steps_timing.items():
            print(f"  {step}: {duration:.2f}s")
    
    if not metrics.success:
        print(f"Error: {metrics.error}")
    
    # Save metrics if requested
    if args.save_metrics:
        metrics_dir = Path("metrics")
        metrics_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = metrics_dir / f"{args.environment}_test_metrics_{timestamp}.json"
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
        print(f"\nMetrics saved to: {metrics_file}")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
