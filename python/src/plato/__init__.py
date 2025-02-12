"""This module provides classes and methods for interacting with the Plato API."""

import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import httpx

from plato.models.test_case import TestCase as TestCaseModel

BASE_URL = "http://localhost:25565"


class Plato:
    @classmethod
    async def create_run_group(
        cls,
        name: str,
        api_key: Optional[str] = None,
    ):
        api_key = api_key or os.environ.get("PLATO_API_KEY")
        if not api_key:
            raise Exception("PLATO_API_KEY is not set")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/runs/group",
                headers={"x-api-key": api_key},
                json={"name": name},
            )

        if response.status_code != 200:
            raise Exception(f"Failed to create run group: {response.text}")

        json_data = response.json()
        return json_data["publicId"]

    @classmethod
    async def start_session(
        cls,
        test_case: TestCaseModel,
        run_group_id: str,
        agent_version: str,
        browser_cdp_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        api_key = api_key or os.environ.get("PLATO_API_KEY")
        if not api_key:
            raise Exception("PLATO_API_KEY is not set")

        assert not browser_cdp_url, "passing browser_cdp_url is not supported yet"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/runs/group/{run_group_id}/run",
                headers={"x-api-key": api_key},
                json={
                    "testCaseId": test_case.id,
                    "version": agent_version,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Failed to start session: {response.text}")

        session_id = response.json()["session_id"]

        # Poll the run session until it has a cdp url. max timeout of 2m
        timeout_at = time.time() + 120
        async with httpx.AsyncClient() as client:
            while time.time() < timeout_at:
                response = await client.get(f"{BASE_URL}/api/runs/{session_id}")
                if response.status_code != 200:
                    raise Exception(f"Failed to get session: {response.text}")

                if response.json()["cdpUrl"]:
                    return response.json()["cdpUrl"]

                await asyncio.sleep(3)

        raise Exception("Timed out waiting for cdp url")

    @classmethod
    async def get_test_cases(
        cls, test_case_set_id: str, api_key: Optional[str] = None
    ) -> List[TestCaseModel]:
        api_key = api_key or os.environ.get("PLATO_API_KEY")
        if not api_key:
            raise Exception("PLATO_API_KEY is not set")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/testcases/sets/{test_case_set_id}/testcases",
                headers={"x-api-key": api_key},
            )
            if response.status_code != 200:
                raise Exception(f"Failed to get test cases: {response.text}")

        response = response.json()
        if not response["success"]:
            raise Exception(f"Failed to get test cases: {response.get('message')}")

        test_cases = [
            TestCaseModel.model_validate(test_case)
            for test_case in response["testcases"]
        ]
        return test_cases
