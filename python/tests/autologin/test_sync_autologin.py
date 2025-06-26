import time
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any
import json
from pathlib import Path
import argparse

from playwright.sync_api import sync_playwright
from plato.models import PlatoTask
from plato.sync_sdk import SyncPlato
from plato.sync_env import SyncPlatoEnvironment

from dotenv import load_dotenv

load_dotenv('.env')

# Create necessary directories at startup
SCREENSHOTS_DIR = Path("screenshots/sync_autologin")
FINAL_SCREENSHOTS_DIR = Path("screenshots/sync_autologin/final")
METRICS_DIR = Path("metrics")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
FINAL_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(exist_ok=True)

class SimulatorTestMetrics:
    def __init__(self, simulator_name: str):
        self.simulator_name = simulator_name
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.error = None
        self.environment_id = None
        self.steps_timing = {}
        self.tasks_count = 0
        self.login_attempted = False
        self.login_successful = False

    def add_step_timing(self, step_name: str, duration: float):
        self.steps_timing[step_name] = duration

    def set_environment_id(self, env_id: str):
        self.environment_id = env_id

    def set_tasks_count(self, count: int):
        self.tasks_count = count

    def set_login_result(self, attempted: bool, successful: bool):
        self.login_attempted = attempted
        self.login_successful = successful

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
            "simulator_name": self.simulator_name,
            "success": self.success,
            "total_duration": self.total_duration,
            "environment_id": self.environment_id,
            "steps_timing": self.steps_timing,
            "tasks_count": self.tasks_count,
            "login_attempted": self.login_attempted,
            "login_successful": self.login_successful,
            "error": self.error
        }

def test_login_functionality(env, page, simulator_name: str, test_id: str) -> tuple[bool, bool]:
    """
    Test login functionality using the environment's built-in login method.
    Returns (login_attempted, login_successful)
    """
    login_attempted = False
    login_successful = False
    
    try:
        # Take initial screenshot
        page.screenshot(path=str(SCREENSHOTS_DIR / f"{simulator_name}_{test_id}_initial.png"))
        
        # Wait a bit for page to fully load
        page.wait_for_timeout(2000)
        
        print(f"Testing login functionality for {simulator_name} using built-in login method")
        
        try:
            # Use the environment's built-in login method
            login_attempted = True
            env.login(page)
            login_successful = True
            print(f"Login completed successfully for {simulator_name}")
            
            # Take screenshot after successful login
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{simulator_name}_{test_id}_after_login.png"))
            
        except Exception as e:
            print(f"Login failed for {simulator_name}: {str(e)}")
            login_successful = False
            
            # Take screenshot after failed login attempt
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{simulator_name}_{test_id}_login_failed.png"))
            
    except Exception as e:
        print(f"Error in login functionality test for {simulator_name}: {e}")
    
    return login_attempted, login_successful

def run_single_simulator_test(simulator: Dict[str, Any]) -> SimulatorTestMetrics:
    """Run a single test for a specific simulator."""
    simulator_name = simulator["name"]
    metrics = SimulatorTestMetrics(simulator_name)
    
    try:
        print(f"\n{'='*60}")
        print(f"Testing Simulator: {simulator_name}")
        print(f"{'='*60}")
        
        # Initialize the client
        step_start = time.time()
        client = SyncPlato()
        
        # Load tasks for this simulator
        try:
            tasks = client.load_tasks(simulator_name)
            metrics.set_tasks_count(len(tasks))
            print(f"Loaded {len(tasks)} tasks for {simulator_name}")
        except Exception as e:
            print(f"Could not load tasks for {simulator_name}: {e}")
            tasks = []
            metrics.set_tasks_count(0)
        
        # Create and initialize the environment
        env = client.make_environment(simulator_name, open_page_on_start=True)
        metrics.add_step_timing("environment_creation", time.time() - step_start)
        metrics.set_environment_id(env.id)
        print(f"Environment ID: {env.id}")
        
        try:
            # Wait for the environment to be ready
            step_start = time.time()
            print(f"Waiting for environment to be ready...")
            env.wait_for_ready(timeout=300.0)
            metrics.add_step_timing("environment_ready", time.time() - step_start)
            print(f"Environment ready")
            
            # Reset the environment with first task if available
            reset_start = time.time()
            if tasks:
                env.reset(task=tasks[0])
                print(f"Environment reset with task: {tasks[0].name}")
            else:
                env.reset()
                print(f"Environment reset without specific task")
            reset_duration = time.time() - reset_start
            metrics.add_step_timing("environment_reset", reset_duration)
            
            # Get the public URL for browser navigation
            public_url_start = time.time()
            print(f"Getting Public URL...")
            public_url = env.get_public_url()
            public_url_duration = time.time() - public_url_start
            metrics.add_step_timing("public_url_retrieval", public_url_duration)
            print(f"Public URL: {public_url}")
            
            # Create new headless browser and navigate to public URL
            browser_start = time.time()
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                print(f"Created new headless browser")
                
                # Navigate to the public URL
                print(f"Navigating to: {public_url}")
                page.goto(public_url)
                print(f"Successfully navigated to public URL")
                
                # Wait for page to load
                page.wait_for_timeout(2000)
                
                # Test login functionality
                login_start = time.time()
                login_attempted, login_successful = test_login_functionality(
                    env, page, simulator_name, env.id
                )
                metrics.set_login_result(login_attempted, login_successful)
                metrics.add_step_timing("login_test", time.time() - login_start)
                
                # Get final state
                try:
                    state = env.get_state()
                    print(f"Final state: {state}")
                except Exception as e:
                    print(f"Could not get final state: {e}")
                
                # Take final screenshot in special directory
                final_screenshot_path = str(FINAL_SCREENSHOTS_DIR / f"{simulator_name}_{env.id}_final.png")
                page.screenshot(path=final_screenshot_path)
                print(f"Final screenshot taken: {final_screenshot_path}")
                
                # Close the browser
                browser.close()
                print(f"Browser closed")
            
            browser_duration = time.time() - browser_start
            metrics.add_step_timing("browser_operations", browser_duration)
            
            metrics.complete(success=True)
            print(f"Test completed successfully for {simulator_name}")
            
        finally:
            # Always ensure we close the environment
            step_start = time.time()
            metrics.add_step_timing("environment_closure", time.time() - step_start)

            # Close the environment
            env.close()
            print(f"Environment closed")
            
            # Close the client to cleanup requests session
            client.close()
            print(f"Client closed")
            
    except Exception as e:
        metrics.complete(success=False, error=e)
        print(f"Test failed for {simulator_name} with error: {e}")
        return metrics

    return metrics

def test_all_simulators(simulator_name: Optional[str] = None):
    """Test all available simulators or a specific simulator if name is provided."""
    if simulator_name:
        print(f"Starting test for specific simulator: {simulator_name}")
    else:
        print("Starting comprehensive simulator testing...")
    
    try:
        # Initialize client to get simulators list
        client = SyncPlato()
        simulators = client.list_simulators()
        client.close()
        
        # Filter to specific simulator if requested
        if simulator_name:
            matching_simulators = [s for s in simulators if s['name'].lower() == simulator_name.lower()]
            if not matching_simulators:
                available_names = [s['name'] for s in simulators]
                print(f"Error: Simulator '{simulator_name}' not found.")
                print(f"Available simulators: {', '.join(available_names)}")
                return
            simulators = matching_simulators
            print(f"Found simulator: {simulators[0]['name']}")
        else:
            print(f"Found {len(simulators)} enabled simulators")
            for sim in simulators:
                print(f"  - {sim['name']}: {sim.get('description', 'No description')}")
        
        # Run tests for all simulators in parallel using threading
        start_time = time.time()
        
        if len(simulators) > 1:
            print(f"\n\nStarting parallel tests for {len(simulators)} simulators...")
            for sim in simulators:
                print(f"  - {sim['name']}")
        else:
            print(f"\n\nStarting test for simulator: {simulators[0]['name']}")
        
        # Create and start threads for parallel execution
        threads = []
        results = [None] * len(simulators)
        
        def run_simulator_test(index, simulator):
            try:
                results[index] = run_single_simulator_test(simulator)
            except Exception as e:
                print(f"❌ Test failed for {simulator['name']} with exception: {e}")
                # Create a failed metrics object for this simulator
                failed_metrics = SimulatorTestMetrics(simulator['name'])
                failed_metrics.complete(success=False, error=e)
                results[index] = failed_metrics
        
        # Start all threads
        for i, simulator in enumerate(simulators):
            thread = threading.Thread(target=run_simulator_test, args=(i, simulator))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        print(f"\nRunning all {len(simulators)} simulator tests in parallel...")
        for thread in threads:
            thread.join()
        
        # Process results
        all_metrics: List[Dict] = []
        for result in results:
            if result is not None:
                all_metrics.append(result.to_dict())
        
        # Calculate and save aggregate metrics
        end_time = time.time()
        total_duration = end_time - start_time
        successful_tests = sum(1 for m in all_metrics if m["success"])
        login_attempts = sum(1 for m in all_metrics if m["login_attempted"])
        successful_logins = sum(1 for m in all_metrics if m["login_successful"])
        
        aggregate_metrics = {
            "test_type": "single_simulator_test" if simulator_name else "comprehensive_simulator_test",
            "tested_simulator": simulator_name if simulator_name else None,
            "total_simulators": len(simulators),
            "successful_tests": successful_tests,
            "failed_tests": len(simulators) - successful_tests,
            "total_duration": total_duration,
            "login_attempts": login_attempts,
            "successful_logins": successful_logins,
            "login_success_rate": (successful_logins / login_attempts * 100) if login_attempts > 0 else 0,
            "overall_success_rate": (successful_tests / len(simulators)) * 100,
            "individual_simulator_metrics": all_metrics
        }
        
        # Save metrics to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_prefix = f"{simulator_name}_" if simulator_name else ""
        metrics_file = METRICS_DIR / f"{filename_prefix}sync_simulator_autologin_test_{timestamp}.json"
        with open(metrics_file, 'w') as f:
            json.dump(aggregate_metrics, f, indent=2)
        
        # Print summary
        print("\n" + "="*80)
        if simulator_name:
            print(f"SINGLE SIMULATOR SYNC TEST RESULTS - {simulator_name.upper()}")
        else:
            print("COMPREHENSIVE SIMULATOR SYNC TEST RESULTS")
        print("="*80)
        print(f"Total Simulators Tested: {len(simulators)}")
        print(f"Successful Tests: {successful_tests}")
        print(f"Failed Tests: {len(simulators) - successful_tests}")
        print(f"Overall Success Rate: {(successful_tests / len(simulators)) * 100:.2f}%")
        print(f"Total Duration: {total_duration:.2f} seconds (parallel execution)")
        print(f"\nLogin Testing Results:")
        print(f"Login Attempts: {login_attempts}")
        print(f"Successful Logins: {successful_logins}")
        if login_attempts > 0:
            print(f"Login Success Rate: {(successful_logins / login_attempts) * 100:.2f}%")
        
        print(f"\nPer-Simulator Results (executed in parallel):")
        for metric in all_metrics:
            status = "✓" if metric["success"] else "✗"
            login_status = ""
            if metric["login_attempted"]:
                login_status = f" | Login: {'✓' if metric['login_successful'] else '✗'}"
            print(f"  {status} {metric['simulator_name']} ({metric['total_duration']:.2f}s){login_status}")
        
        print(f"\nDetailed metrics saved to: {metrics_file}")
        print(f"Screenshots saved to: {SCREENSHOTS_DIR}")
        print(f"Final screenshots saved to: {FINAL_SCREENSHOTS_DIR}")
        print("="*80)
        
    except Exception as e:
        print(f"Error during comprehensive simulator testing: {e}")
        raise

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Test Plato simulators with autologin functionality (synchronous version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_sync_autologin.py                    # Test all simulators
  python test_sync_autologin.py --simulator espocrm  # Test only EspoCRM
  python test_sync_autologin.py -s doordash          # Test only DoorDash
        """
    )
    parser.add_argument(
        "--simulator", "-s",
        type=str,
        help="Name of a specific simulator to test (case-insensitive). If not provided, all simulators will be tested."
    )
    parser.add_argument(
        "--list-simulators", "-l",
        action="store_true",
        help="List all available simulators and exit"
    )
    
    args = parser.parse_args()
    
    if args.list_simulators:
        # List simulators and exit
        client = SyncPlato()
        simulators = client.list_simulators()
        client.close()
        print(f"Available simulators ({len(simulators)}):")
        for sim in simulators:
            print(f"  - {sim['name']}: {sim.get('description', 'No description')}")
        return
    
    # Run the test
    test_all_simulators(args.simulator)

if __name__ == "__main__":
    main() 