import asyncio
import os
import logging
import unittest
from dotenv import load_dotenv
from plato import Plato
from main import run_task

load_dotenv(dotenv_path=".env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PLATO_API_KEY = os.environ.get("PLATO_API_KEY")
if not PLATO_API_KEY:
    raise ValueError(
        "PLATO_API_KEY environment variable is not set. Please set it in your .env file."
    )

PLATO_API_URL = os.environ.get("PLATO_API_URL", "https://plato.so/api")

class TestPredefinedCases(unittest.TestCase):
    def setUp(self):
        self.client = Plato(base_url=PLATO_API_URL, api_key=PLATO_API_KEY)
        self.test_cases = [
            {
                "simulator": "espocrm",
                "task_name": "create_bruce_wang_contact",
                "agent_version": "browser_use_test",
                "timeout": 400
            }
        ]

    async def run_single_test(self, test_case):
        """Run a single test case using real Plato API and evaluate results"""
        logger.info(f"Running test case: {test_case['task_name']}")
        
        # Get simulator tasks for the specified simulator
        simulator_tasks = await self.client.load_tasks(test_case["simulator"])
        
        # Find the specific task by name
        target_task = None
        for task in simulator_tasks:
            if task.name == test_case["task_name"]:
                target_task = task
                break
        
        if not target_task:
            logger.error(f"Task '{test_case['task_name']}' not found in {test_case['simulator']} simulator")
            return False, None
        
        logger.info(f"Found task: {target_task.name} with prompt: {target_task.prompt}")
        
        try:
            # Create environment and run the task
            env = await self.client.make_environment(target_task.env_id, open_page_on_start=False)
            
            logger.info(f"Waiting for environment to be ready ({target_task.env_id})")
            await env.wait_for_ready()
            logger.info(f"Environment {target_task.env_id} is ready")
            
            # Reset environment and run task
            await env.reset(target_task, agent_version=test_case.get('agent_version', 'browser_use_test'))
            logger.info("Environment reset")
            
            # Run the actual task using the main.py logic
            from main import TASK_SETS, run_browseruse_task, run_openai_cua_task, run_anthropic_cua_task
            
            # Get the base prompt template from the task set configuration
            base_prompt = TASK_SETS[test_case["simulator"]]["base_prompt"]
            
            # Format the prompt with task-specific information
            prompt = base_prompt.format(start_url=target_task.start_url, prompt=target_task.prompt)
            
            cdp_url = await env.get_cdp_url()
            live_view_url = await env.get_live_view_url()
            logger.info(f"Live view URL: {live_view_url}")
            
            agent_version = test_case.get('agent_version', 'browser_use_test')
            
            if "browser_use" in agent_version:
                await run_browseruse_task(cdp_url, prompt, target_task.start_url)
            elif "openai" in agent_version:
                await run_openai_cua_task(cdp_url, prompt, target_task.start_url, env)
            elif "anthropic" in agent_version:
                await run_anthropic_cua_task(cdp_url, prompt, target_task.start_url)
            
            # Evaluate the task
            eval_result = await env.evaluate()
            logger.info(f"Evaluation result: {eval_result}")
            
            # Close environment
            await env.close()
            
            # Determine success based on evaluation
            success = eval_result.get('success', False) if isinstance(eval_result, dict) else bool(eval_result)
            logger.info(f"Test case '{test_case['task_name']}' completed with success: {success}")
            
            return success, eval_result
            
        except Exception as e:
            logger.error(f"Test case '{test_case['task_name']}' failed: {e}")
            return False, str(e)

    async def run_all_tests(self):
        """Run all predefined test cases"""
        results = {}
        
        for test_case in self.test_cases:
            success, eval_result = await self.run_single_test(test_case)
            results[test_case['task_name']] = {
                'success': success,
                'eval_result': eval_result
            }
        
        await self.client.close()
        return results

    def test_create_bruce_wang_contact(self):
        """Test creating Bruce Wang contact in EspoCRM"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(self.run_all_tests())
            test_result = results.get('create_bruce_wang_contact', {})
            self.assertTrue(test_result.get('success', False), 
                          f"Test failed with evaluation: {test_result.get('eval_result')}")
        finally:
            loop.close()

async def main():
    """Main function to run tests directly"""
    tester = TestPredefinedCases()
    tester.setUp()
    
    print("Running predefined test cases...")
    results = await tester.run_all_tests()
    
    print("\nTest Results:")
    for test_name, result in results.items():
        status = "PASSED" if result['success'] else "FAILED"
        print(f"  {test_name}: {status}")
        if result['eval_result']:
            print(f"    Evaluation: {result['eval_result']}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r['success'])
    print(f"\nSummary: {passed_tests}/{total_tests} tests passed")

if __name__ == "__main__":
    asyncio.run(main())
