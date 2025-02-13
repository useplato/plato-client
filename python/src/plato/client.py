# plato_sdk.py

"""
Plato Python SDK

This module provides classes and methods for interacting with the Plato evaluation API.
It defines the following key classes:

- Task: Represents a single task to be evaluated.
- PlatoRunnerConfig: Configuration for task execution and browser management.
- EvalSummary & EvalResult: Containers for evaluation results.
- Plato: Main client for running evaluations.
- PlatoSession: Manages a browser session for a task.
"""

import asyncio
import os
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx
from pydantic import BaseModel

from .models.eval_results import EvalResult, EvalSummary
from .models.task import Task

DEFAULT_BASE_URL = "https://plato.so"

class PlatoRunnerConfig(BaseModel):
    """
    Configuration for task execution and browser management.
    """

    name: str
    data: List[Task]
    task: Callable[[Task, str], Awaitable[Any]]
    trial_count: int = 1
    timeout: int = 1800000
    max_concurrency: int = 15
    custom_browser: Optional[Callable[[Task], Awaitable[str]]] = None
    custom_scores: List[Callable[[Dict[str, Any]], Awaitable[float]]] = []


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
        config: PlatoRunnerConfig,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.name = name
        self.run_batch_id = run_batch_id
        self.config = config

    async def _run_task(self, task: Task) -> dict:
        """
        Runs a single evaluation task:
          1. Start a browser session.
          2. Execute the runner task.
          3. Compute custom scores (if any).
          4. Close the session.
        """
        try:
            session = await PlatoSession.start(self, task)
            output = await self.config.task(task, session.cdp_url)
            custom_scores = []
            for score_func in self.config.custom_scores:
                score = await score_func(
                    {
                        "input": task,
                        "output": output,
                        "expected": getattr(task, "expected", None),
                    }
                )
                custom_scores.append(score)
            return {
                "input": task.model_dump(mode="json"),
                "output": output,
                "custom_scores": custom_scores,
            }
        finally:
            await session.close()

    async def run(self) -> EvalResult:
        """
        Executes all tasks based on trial_count and max_concurrency.
        Returns an EvalResult containing a summary and all task results.
        """
        results = []
        # Create a list of tasks repeated trial_count times.
        queue = [
            task for task in self.config.data for _ in range(self.config.trial_count)
        ]
        semaphore = asyncio.Semaphore(self.config.max_concurrency)

        async def process_task(task: Task):
            async with semaphore:
                try:
                    res = await self._run_task(task)
                    results.append(res)
                except Exception as e:
                    print(f"Error processing {task.name}: {e}")

        workers = [process_task(task) for task in queue]

        try:
            await asyncio.wait_for(
                asyncio.gather(*workers), timeout=self.config.timeout / 1000
            )
        except asyncio.TimeoutError:
            raise Exception(f"Evaluation timed out after {self.config.timeout}ms")

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
    async def start(
        name: str,
        config: PlatoRunnerConfig,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> EvalResult:
        """
        Static method to initialize a run group and execute the evaluation.

        :param name: The version or name for this evaluation run.
        :param config: Configuration for task execution and browser management.
        :param api_key: (Optional) API key; if not provided, uses the PLATO_API_KEY environment variable.
        :param base_url: (Optional) Base URL of the Plato API.
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
                json={"name": config.name},
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
            config=config,
        )
        return await plato.run()

    @staticmethod
    async def get_dataset(
        dataset_id: str, api_key: Optional[str] = None, base_url: Optional[str] = None
    ) -> List[Task]:
        """
        Fetches a dataset from the Plato API.
        """
        base_url = base_url or DEFAULT_BASE_URL
        api_key = api_key or os.getenv("PLATO_API_KEY")
        if not api_key:
            raise Exception("PLATO_API_KEY is not set")

        headers = {"Content-Type": "application/json", "x-api-key": api_key}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/api/testcases/sets/{dataset_id}/testcases", headers=headers
            )
            if response.status_code != 200:
                raise Exception(f"Failed to get dataset: {response.text}")
            data = response.json()
            if not data["success"]:
                raise Exception(f"Failed to get dataset: {data['message']}")
            return [Task.model_validate(task) for task in data["testcases"]]


class PlatoSession:
    """
    Represents a browser session associated with a task.
    """

    def __init__(self, plato: Plato, task: Task, cdp_url: str, session_id: str):
        self.plato = plato
        self.task = task
        self.cdp_url = cdp_url
        self.session_id = session_id

    @staticmethod
    async def start(plato: Plato, task: Task) -> "PlatoSession":
        """
        Starts a new browser session for the given task.
        If a custom_browser function is provided in the config, it will be used to get the CDP URL.
        Otherwise, polls the Plato API until a CDP URL is available or a timeout occurs.
        """
        headers = {"Content-Type": "application/json", "x-api-key": plato.api_key}
        payload = {"version": plato.name, "testCase": task.model_dump(mode="json")}

        # Start the session first
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

        # If custom browser is provided, use it to get CDP URL
        if plato.config.custom_browser:
            cdp_url = await plato.config.custom_browser(task)
            return PlatoSession(plato, task, cdp_url, session_id)

        # Otherwise poll for CDP URL from Plato API
        cdp_url = None
        timeout_seconds = 60  # 1 minute
        start_time = time.time()

        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout_seconds:
                resp = await client.get(f"{plato.base_url}/api/runs/{session_id}")
                run_data = resp.json()
                if run_data.get("cdpUrl"):
                    cdp_url = run_data.get("cdpUrl")
                    break
                await asyncio.sleep(1)

        if not cdp_url:
            raise Exception("Failed to start browser session")

        return PlatoSession(plato, task, cdp_url, session_id)

    @staticmethod
    async def terminate(plato: "Plato", session_id: str) -> None:
        """
        Terminates a browser session.
        """
        try:
            headers = {"x-api-key": plato.api_key}
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{plato.base_url}/api/runs/{session_id}/terminate",
                    headers=headers,
                )
        except Exception as e:
            print(f"Error terminating session: {e}")

    async def close(self) -> None:
        """
        Deprecated: Use end() instead.
        Closes the browser session.
        """
        return await self.terminate(self.plato, self.session_id)

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
