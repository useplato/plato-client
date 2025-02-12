# plato_sdk.py

"""
Plato Python SDK

This module provides classes and methods for interacting with the Plato evaluation API.
It defines the following key classes:

- TestCase: Represents a single test case.
- Evaluator: Holds test cases, an async task function, and custom scoring functions.
- EvalSummary & EvalResult: Containers for evaluation results.
- Plato: Main client for running evaluations.
- PlatoSession: Manages a browser session for a test case.
"""

import asyncio
import os
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx
from pydantic import BaseModel

from .models.eval_results import EvalResult, EvalSummary
from .models.test_case import TestCase

DEFAULT_BASE_URL = "https://plato.so"


class Evaluator:
    def __init__(
        self,
        name: str,
        data: List[TestCase],
        task: Callable[[TestCase, "PlatoSession"], Awaitable[Any]],
        custom_scores: Optional[
            List[Callable[[Dict[str, Any]], Awaitable[float]]]
        ] = None,
        trial_count: int = 1,
        timeout: int = 600000,
        max_concurrency: int = 15,
    ):
        """
        :param name: Name of the evaluator.
        :param data: A list of TestCase instances.
        :param task: An async function that takes a TestCase and a PlatoSession and returns output.
        :param custom_scores: (Optional) A list of async functions to compute custom scores.
        :param trial_count: Number of trials per test case.
        :param timeout: Overall evaluation timeout in milliseconds.
        :param max_concurrency: Maximum number of concurrent task executions.
        """
        self.name = name
        self.data = data
        self.task = task
        self.custom_scores = custom_scores or []
        self.trial_count = trial_count
        self.timeout = timeout
        self.max_concurrency = max_concurrency


class Plato:
    """
    The main client for interacting with the Plato evaluation API.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        name: str,
        run_batch_id: str,
        evaluator: Evaluator,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.name = name
        self.run_batch_id = run_batch_id
        self.evaluator = evaluator

        self.max_concurrency = evaluator.max_concurrency
        self.trial_count = evaluator.trial_count
        self.timeout = evaluator.timeout

    async def _run_task(self, test_case: TestCase) -> dict:
        """
        Runs a single evaluation task:
          1. Start a browser session.
          2. Execute the evaluator task.
          3. Compute custom scores (if any).
          4. Close the session.
        """
        session = await PlatoSession.start(self, test_case)
        try:
            output = await self.evaluator.task(test_case, session)
            custom_scores = []
            for score_func in self.evaluator.custom_scores:
                score = await score_func(
                    {
                        "input": test_case,
                        "output": output,
                        "expected": getattr(test_case, "expected", None),
                    }
                )
                custom_scores.append(score)
            # If no custom scores are provided, default score is 1.0.
            score = sum(custom_scores) / len(custom_scores) if custom_scores else 1.0
            return {
                "input": test_case.to_dict(),
                "output": output,
                "custom_scores": custom_scores,
                "score": score,
            }
        finally:
            await session.close()

    async def run(self) -> EvalResult:
        """
        Executes all test cases based on trial_count and max_concurrency.
        Returns an EvalResult containing a summary and all task results.
        """
        results = []
        # Create a list of test cases repeated trial_count times.
        queue = [tc for tc in self.evaluator.data for _ in range(self.trial_count)]
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_task(tc: TestCase):
            async with semaphore:
                try:
                    res = await self._run_task(tc)
                    results.append(res)
                except Exception as e:
                    print(f"Error processing {tc.name}: {e}")

        workers = [process_task(tc) for tc in queue]

        try:
            await asyncio.wait_for(
                asyncio.gather(*workers), timeout=self.timeout / 1000
            )
        except asyncio.TimeoutError:
            raise Exception(f"Evaluation timed out after {self.timeout}ms")

        total = len(results)
        success = len([r for r in results if r.get("score", 0) > 0])
        failure = total - success
        average_score = (
            sum(r.get("score", 0) for r in results) / total if total > 0 else 0
        )

        summary = EvalSummary(
            total=total, success=success, failure=failure, score=average_score
        )
        return EvalResult(summary=summary, results=results)

    @staticmethod
    async def eval(
        name: str,
        evaluator: Evaluator,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> EvalResult:
        """
        Static method to initialize a run group and execute the evaluation.

        :param name: The version or name for this evaluation run.
        :param evaluator: An Evaluator instance containing test cases and the task function.
        :param base_url: (Optional) Base URL of the Plato API.
        :param api_key: (Optional) API key; if not provided, uses the PLATO_API_KEY environment variable.
        :return: An EvalResult containing a summary and task results.
        """
        base_url = base_url or DEFAULT_BASE_URL
        api_key = api_key or os.getenv("PLATO_API_KEY")
        if not api_key:
            raise Exception("PLATO_API_KEY is not set")

        headers = {"Content-Type": "application/json", "x-api-key": api_key}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/runs/group",
                json={"name": evaluator.name},
                headers=headers,
            )
            if response.status_code != 200:
                raise Exception(f"Failed to initialize Plato: {response.text}")
            data = response.json()

        run_batch_id = data.get("publicId")
        if not run_batch_id:
            raise Exception("No run batch ID returned from Plato API")
        plato = Plato(
            api_key=api_key,
            base_url=base_url,
            name=name,
            run_batch_id=run_batch_id,
            evaluator=evaluator,
        )
        return await plato.run()


class PlatoSession:
    """
    Represents a browser session associated with a test case.
    """

    def __init__(
        self, plato: Plato, test_case: TestCase, cdp_url: str, session_id: str
    ):
        self.plato = plato
        self.test_case = test_case
        self.cdp_url = cdp_url
        self.session_id = session_id

    @staticmethod
    async def start(plato: Plato, test_case: TestCase) -> "PlatoSession":
        """
        Starts a new browser session for the given test case.
        Polls the Plato API until a CDP URL is available or a timeout occurs.
        """
        headers = {"Content-Type": "application/json", "x-api-key": plato.api_key}
        payload = {"version": plato.name, "testCase": test_case.to_dict()}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{plato.base_url}/api/runs/group/{plato.run_batch_id}/run",
                json=payload,
                headers=headers,
            )
            if response.status_code != 200:
                raise Exception(f"Failed to start session: {response.text}")
            data = response.json()

        session_id = data.get("session_id")
        if not session_id:
            raise Exception("No session_id returned from Plato API")

        cdp_url = None
        timeout_seconds = 600  # 10 minutes
        start_time = time.time()

        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout_seconds:
                resp = await client.get(f"{plato.base_url}/api/runs/{session_id}")
                run_data = resp.json()
                if run_data.get("cdpUrl"):
                    cdp_url = run_data.get("cdpUrl")
                    break
                await asyncio.sleep(3)

        if not cdp_url:
            raise Exception("Failed to start browser session")

        return PlatoSession(plato, test_case, cdp_url, session_id)

    async def close(self) -> None:
        """
        Closes the browser session.
        (Implement any necessary cleanup with the Plato API.)
        """
        headers = {"Content-Type": "application/json", "x-api-key": self.plato.api_key}
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.plato.base_url}/api/runs/{self.session_id}/close",
                headers=headers,
            )
        return

    async def log(self, message: str) -> None:
        """
        Sends a log message to the Plato server for this session.
        """
        headers = {"Content-Type": "application/json", "x-api-key": self.plato.api_key}
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.plato.base_url}/api/runs/{self.session_id}/log",
                json={"message": message},
                headers=headers,
            )
        return

    async def score(self) -> None:
        """
        Sends the score to the Plato server for this session.
        """
        headers = {"Content-Type": "application/json", "x-api-key": self.plato.api_key}
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.plato.base_url}/api/runs/{self.session_id}/score",
                headers=headers,
            )
        return
