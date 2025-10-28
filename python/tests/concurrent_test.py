import logging
import os
import asyncio
import argparse
import time
from plato.sdk import Plato
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()
BASE_URL = os.getenv("PLATO_BASE_URL")
API_KEY = os.getenv("PLATO_API_KEY")

async def run_single_test(test_id: int, client: Plato):
    """Run a single test instance"""
    env = None
    error_info = None
    try:
        logger.info(f"[Test {test_id}] Starting environment creation")
        env = await client.make_environment(
            "webarenacms",
            fast=True,
            interface_type=None,
            tag='prod-latest'
        )
        await env.wait_for_ready()

        logger.info(f"[Test {test_id}] Environment ready, performing reset")
        try:
            await env.reset()
        except Exception as e:
            logger.error(f"[Test {test_id}] Reset failed: {e}")
            error_info = {"test_id": test_id, "stage": "reset", "error": str(e)}
            raise

        public_url = await env.get_public_url()
        logger.info(f"[Test {test_id}] Public URL: {public_url}")

        logger.info(f"[Test {test_id}] Completed successfully")
        return {"test_id": test_id, "success": True}
    except Exception as e:
        logger.error(f"[Test {test_id}] Failed with error: {e}")
        if not error_info:
            error_info = {"test_id": test_id, "stage": "unknown", "error": str(e)}
        return {"test_id": test_id, "success": False, "error_info": error_info}
    finally:
        if env:
            try:
                logger.info(f"[Test {test_id}] Closing environment")
                await env.close()
            except Exception as e:
                logger.error(f"[Test {test_id}] Error closing environment: {e}")


async def run_concurrent_batch(batch_num: int, concurrency: int, client: Plato):
    """Run a batch of tests concurrently"""
    logger.info(f"[Batch {batch_num}] Starting {concurrency} concurrent tests")

    tasks = []
    for i in range(concurrency):
        test_id = batch_num * concurrency + i
        tasks.append(run_single_test(test_id, client))

    results = await asyncio.gather(*tasks, return_exceptions=False)

    success_count = sum(1 for r in results if r.get("success", False))
    failure_count = len(results) - success_count

    # Check for any reset errors
    for result in results:
        if not result.get("success", True):
            error_info = result.get("error_info", {})
            if error_info.get("stage") == "reset":
                logger.error(f"[Batch {batch_num}] Reset error detected, waiting 30 minutes before closing")
                await asyncio.sleep(1800)  # Wait 30 minutes (1800 seconds)
                break

    logger.info(f"[Batch {batch_num}] Completed: {success_count} succeeded, {failure_count} failed")
    return results

async def main(concurrency: int, num_tests: int):
    """
    Main function to run tests with specified concurrency and number of tests

    Args:
        concurrency: Number of tests to run concurrently in each batch
        num_tests: Total number of test batches to run
    """
    client = Plato(base_url=BASE_URL, api_key=API_KEY)

    logger.info(f"Starting test run with concurrency={concurrency}, num_tests={num_tests}")

    all_results = []
    try:
        for batch_num in range(num_tests):
            logger.info(f"\n{'='*50}")
            logger.info(f"Running batch {batch_num + 1}/{num_tests}")
            logger.info(f"{'='*50}\n")

            try:
                batch_results = await run_concurrent_batch(batch_num, concurrency, client)
                all_results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch {batch_num} failed with error: {e}")

            # Small delay between batches
            if batch_num < num_tests - 1:
                logger.info("Waiting 5 seconds before next batch...")
                await asyncio.sleep(5)

        # Print summary
        logger.info("\n" + "="*50)
        logger.info("TEST SUMMARY")
        logger.info("="*50)

        total_tests = len(all_results)
        successful_tests = [r for r in all_results if r.get("success", False)]
        failed_tests = [r for r in all_results if not r.get("success", True)]

        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Successful: {len(successful_tests)}")
        logger.info(f"Failed: {len(failed_tests)}")

        if failed_tests:
            logger.info("\nFailed tests details:")
            for result in failed_tests:
                error_info = result.get("error_info", {})
                test_id = error_info.get("test_id", "unknown")
                stage = error_info.get("stage", "unknown")
                error = error_info.get("error", "unknown error")
                logger.error(f"  Test {test_id} failed at {stage}: {error}")

        logger.info("="*50)

    except Exception as e:
        logger.error(f"Test run failed: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run concurrent Plato environment tests')
    parser.add_argument('--concurrency', type=int, default=2,
                        help='Number of tests to run concurrently (default: 2)')
    parser.add_argument('--num-tests', type=int, default=5,
                        help='Number of test batches to run (default: 5)')

    args = parser.parse_args()

    logger.info(f"Configuration: concurrency={args.concurrency}, num_tests={args.num_tests}")

    asyncio.run(main(args.concurrency, args.num_tests))
