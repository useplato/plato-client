import asyncio
import time
from datetime import datetime
from typing import List, Dict
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from plato.sdk import Plato

from dotenv import load_dotenv

load_dotenv()

# Create necessary directories at startup
METRICS_DIR = Path("metrics")
METRICS_DIR.mkdir(exist_ok=True)

@dataclass
class BatchMetrics:
    batch_id: int
    start_time: float
    end_time: float = None
    environments: List[str] = None
    success: bool = False
    error: str = None
    steps_timing: Dict[str, float] = None

    def __post_init__(self):
        if self.environments is None:
            self.environments = []
        if self.steps_timing is None:
            self.steps_timing = {}

    def complete(self, success: bool, error=None):
        self.end_time = time.time()
        self.success = success
        self.error = str(error) if error else None

    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return 0

    def to_dict(self) -> dict:
        return asdict(self)

async def run_single_batch(batch_id: int, num_browsers: int = 16) -> BatchMetrics:
    """Run a single batch of browser environments."""
    metrics = BatchMetrics(batch_id=batch_id, start_time=time.time())
    
    try:
        # Initialize the client
        client = Plato()
        
        # Create all environments for this batch
        print(f"Batch {batch_id}: Creating {num_browsers} environments...")
        creation_start = time.time()
        
        # Create environments concurrently
        create_tasks = []
        for i in range(num_browsers):
            create_tasks.append(client.make_environment("espocrm"))
        
        environments = await asyncio.gather(*create_tasks)
        metrics.environments = [env.id for env in environments]
        metrics.steps_timing["environment_creation"] = time.time() - creation_start
        
        try:
            # Wait for all environments to be ready
            print(f"Batch {batch_id}: Waiting for all environments to be ready...")
            ready_start = time.time()
            ready_tasks = [env.wait_for_ready(timeout=600.0) for env in environments]
            await asyncio.gather(*ready_tasks)
            metrics.steps_timing["environments_ready"] = time.time() - ready_start
            print(f"Batch {batch_id}: All environments ready")

            # Reset all environments
            print(f"Batch {batch_id}: Resetting all environments...")
            reset_start = time.time()
            reset_tasks = [env.reset() for env in environments]
            await asyncio.gather(*reset_tasks)
            metrics.steps_timing["environments_reset"] = time.time() - reset_start
            print(f"Batch {batch_id}: All environments reset")

            # Brief pause to simulate some work being done
            await asyncio.sleep(5)
            
            metrics.complete(success=True)
            
        finally:
            # Always ensure we close all environments
            print(f"Batch {batch_id}: Closing all environments...")
            close_start = time.time()
            close_tasks = [env.close() for env in environments]
            await asyncio.gather(*close_tasks)
            metrics.steps_timing["environments_closure"] = time.time() - close_start
            print(f"Batch {batch_id}: All environments closed")
            
            # Close the client
            await client.close()
            
    except Exception as e:
        print(f"Batch {batch_id} failed with error: {e}")
        metrics.complete(success=False, error=e)
        return metrics

    print(f"Batch {batch_id} completed successfully")
    return metrics

async def run_batch_load_test(num_batches: int = 6, browsers_per_batch: int = 16):
    """
    Run load test with multiple batches of browser environments.
    
    Args:
        num_batches (int): Number of batches to run concurrently
        browsers_per_batch (int): Number of browsers in each batch
    """
    all_metrics: List[Dict] = []
    start_time = time.time()

    print(f"Starting batch load test: {num_batches} batches, {browsers_per_batch} browsers per batch")
    
    # Run all batches concurrently
    batch_tasks = [
        run_single_batch(batch_id, browsers_per_batch)
        for batch_id in range(num_batches)
    ]
    
    print(f"Starting all {num_batches} batches...")
    batch_results = await asyncio.gather(*batch_tasks)
    all_metrics = [m.to_dict() for m in batch_results]

    # Calculate aggregate metrics
    end_time = time.time()
    total_duration = end_time - start_time
    successful_batches = sum(1 for m in batch_results if m.success)
    total_environments = sum(len(m.environments) for m in batch_results)
    
    # Calculate step-specific metrics
    step_averages = {}
    for step_name in ["environment_creation", "environments_ready", "environments_reset", 
                     "environments_closure"]:
        step_times = [m.steps_timing.get(step_name, 0) for m in batch_results if m.steps_timing.get(step_name)]
        if step_times:
            step_averages[step_name] = {
                "average": sum(step_times) / len(step_times),
                "min": min(step_times),
                "max": max(step_times)
            }
    
    aggregate_metrics = {
        "test_type": "batch_browser_load_test",
        "total_batches": num_batches,
        "browsers_per_batch": browsers_per_batch,
        "total_environments": total_environments,
        "successful_batches": successful_batches,
        "failed_batches": num_batches - successful_batches,
        "total_duration": total_duration,
        "environments_per_second": total_environments / total_duration,
        "success_rate": (successful_batches / num_batches) * 100,
        "step_averages": step_averages,
        "batch_metrics": all_metrics
    }

    # Save metrics to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = METRICS_DIR / f"batch_browser_loadtest_metrics_{timestamp}.json"
    with open(metrics_file, 'w') as f:
        json.dump(aggregate_metrics, f, indent=2)

    print("\n" + "="*60)
    print("BATCH BROWSER LOAD TEST RESULTS")
    print("="*60)
    print(f"Total Batches: {num_batches}")
    print(f"Browsers per Batch: {browsers_per_batch}")
    print(f"Total Environments: {total_environments}")
    print(f"Successful Batches: {successful_batches}")
    print(f"Failed Batches: {num_batches - successful_batches}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Environments per Second: {total_environments / total_duration:.2f}")
    print(f"Success Rate: {(successful_batches / num_batches) * 100:.2f}%")
    
    if step_averages:
        print(f"\nStep Performance (Average Duration per Batch):")
        for step, times in step_averages.items():
            print(f"  {step}: {times['average']:.2f}s (min: {times['min']:.2f}s, max: {times['max']:.2f}s)")
    
    print(f"\nDetailed metrics saved to: {metrics_file}")
    print("="*60)

if __name__ == "__main__":
    # Configure these parameters as needed
    NUM_BATCHES = 6          # Number of batches to run concurrently
    BROWSERS_PER_BATCH = 16  # Number of browsers in each batch
    
    asyncio.run(run_batch_load_test(NUM_BATCHES, BROWSERS_PER_BATCH)) 