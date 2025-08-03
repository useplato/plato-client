import asyncio
import os
import argparse
import logging
from collections import defaultdict
from typing import List, Dict, Any

from plato import Plato, PlatoTask
from dotenv import load_dotenv

# Import functions from main.py
from main import (
    create_environment_pool,
    run_with_semaphore,
)

load_dotenv(dotenv_path=".env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load required environment variables
PLATO_API_KEY = os.environ.get("PLATO_API_KEY")
if not PLATO_API_KEY:
    raise ValueError(
        "PLATO_API_KEY environment variable is not set. Please set it in your .env file."
    )

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is not set. Please set it in your .env file."


class BenchmarkPlato(Plato):
    """Extended Plato client with agent artifact and session querying capabilities."""

    async def list_agent_artifacts(self) -> List[Dict[str, Any]]:
        """Query all agent artifacts using the /agent-artifacts endpoint.

        Returns:
            List[Dict[str, Any]]: List of agent artifacts with their metadata.
        """
        headers = {"X-API-Key": self.api_key}
        async with self.http_session.get(
            f"{self.base_url}/agent-artifacts/", headers=headers
        ) as response:
            response.raise_for_status()
            res = await response.json()
            return res["artifacts"]

    async def list_sessions(
        self,
        simulator_ids: List[str] = None,
        agent_artifact_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Query sessions using the /session route with optional filters.

        Args:
            simulator_ids: List of simulator IDs to filter by
            agent_artifact_ids: List of agent artifact IDs to filter by

        Returns:
            List[Dict[str, Any]]: List of sessions matching the filters.
        """
        headers = {"X-API-Key": self.api_key}
        params = {}

        if simulator_ids:
            params["simulatorIds"] = ",".join(str(sid) for sid in simulator_ids)
        if agent_artifact_ids:
            params["agentArtifactIds"] = ",".join(str(aid) for aid in agent_artifact_ids)

        params["pageSize"] = 5000

        async with self.http_session.get(
            f"{self.base_url}/session/", headers=headers, params=params
        ) as response:
            response.raise_for_status()
            res = await response.json()
            return res["sessions"]

def filter_agent_artifacts(agent_artifacts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Filter and group agent artifacts by their alias type.

    Args:
        agent_artifacts: List of all agent artifacts from the API

    Returns:
        Dict mapping agent type to list of matching artifacts
    """
    filtered_artifacts = {
        "browser_use": [],
        "anthropic": [],
        "openai": []
    }

    for artifact in agent_artifacts:
        alias = artifact.get("alias", "").lower()

        if "browser_use" in alias:
            filtered_artifacts["browser_use"].append(artifact)
        elif "anthropic" in alias:
            filtered_artifacts["anthropic"].append(artifact)
        elif "openai" in alias:
            filtered_artifacts["openai"].append(artifact)

    logger.info(f"Filtered agent artifacts: {len(filtered_artifacts['browser_use'])} browser_use, "
                f"{len(filtered_artifacts['anthropic'])} anthropic, "
                f"{len(filtered_artifacts['openai'])} openai")

    return filtered_artifacts


def count_sessions_by_agent_and_testcase(sessions: List[Dict[str, Any]], agent_artifacts: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, int]]:
    """Count sessions grouped by agent type and test case.

    Args:
        sessions: List of sessions from the API
        agent_artifacts: Filtered agent artifacts grouped by type

    Returns:
        Dict mapping agent_type -> testcase_id -> session_count
    """
    # Create mapping from artifact ID to agent type
    artifact_id_to_type = {}
    for agent_type, artifacts in agent_artifacts.items():
        for artifact in artifacts:
            artifact_id_to_type[artifact["id"]] = agent_type

    # Count sessions
    session_counts = defaultdict(lambda: defaultdict(int))

    for session in sessions:
        agent_artifact_id = session.get("agentArtifactId")
        testcase_id = session.get("testCase", {}).get("publicId")

        if agent_artifact_id in artifact_id_to_type and testcase_id:
            agent_type = artifact_id_to_type[agent_artifact_id]
            session_counts[agent_type][testcase_id] += 1

    return dict(session_counts)


def find_missing_sessions(
    session_counts: Dict[str, Dict[str, int]],
    testcases: List[PlatoTask],
    target_sessions: int = 5
) -> Dict[str, List[str]]:
    """Find agent types that need more sessions for specific test cases.

    Args:
        session_counts: Current session counts by agent type and test case
        testcases: List of test cases to check
        target_sessions: Target number of sessions per agent type per test case

    Returns:
        Dict mapping agent_type -> list of testcase_ids needing more sessions
    """
    missing_sessions = defaultdict(list)

    for testcase in testcases:
        testcase_id = testcase.public_id

        for agent_type in ["browser_use", "anthropic", "openai"]:
            current_count = session_counts.get(agent_type, {}).get(testcase_id, 0)

            if current_count < target_sessions:
                missing_sessions[agent_type].append(testcase_id)
                logger.info(f"Agent {agent_type} needs {target_sessions - current_count} more sessions for testcase {testcase.name}")

    return dict(missing_sessions)


async def create_missing_sessions(
    client: BenchmarkPlato,
    missing_sessions: Dict[str, List[str]],
    testcases: List[PlatoTask],
    simulator_name: str,
    concurrency: int = 5,
    target_sessions: int = 5
):
    """Create missing sessions for agent types that don't have enough.

    Args:
        client: Plato client instance
        missing_sessions: Dict of agent types and their missing testcase IDs
        testcases: List of all test cases
        simulator_name: Name of the simulator
        concurrency: Number of concurrent sessions to run
        target_sessions: Target number of sessions per agent type per test case
    """
    # Create testcase lookup
    testcase_lookup = {task.public_id: task for task in testcases}

    # Setup semaphore for concurrency
    sem = asyncio.Semaphore(concurrency)

    # Create environment pool
    env_pool, environments = await create_environment_pool(client, concurrency, testcases)

    try:
        # Create tasks for all missing sessions
        async_tasks = []

        for agent_type, testcase_ids in missing_sessions.items():
            # Map agent type to version string
            agent_version_map = {
                "browser_use": "browser_use",
                "anthropic": "anthropic",
                "openai": "openai_cua"
            }
            agent_version = agent_version_map[agent_type]

            for testcase_id in testcase_ids:
                if testcase_id not in testcase_lookup:
                    logger.warning(f"Testcase {testcase_id} not found in testcase list")
                    continue

                testcase = testcase_lookup[testcase_id]

                # Get current session count for this agent type and testcase
                current_sessions = await get_current_session_count(client, agent_type, testcase_id, simulator_name)
                sessions_needed = max(0, target_sessions - current_sessions)

                for _ in range(sessions_needed):
                    async_tasks.append(
                        run_with_semaphore(
                            sem, env_pool, testcase,
                            agent_version=agent_version,
                            task_set=simulator_name.lower()
                        )
                    )

        if async_tasks:
            logger.info(f"Creating {len(async_tasks)} missing sessions...")
            await asyncio.gather(*async_tasks)
            logger.info("All missing sessions created successfully!")
        else:
            logger.info("No missing sessions to create.")

    finally:
        # Close all environments in the pool
        logger.info("Closing all environments in pool")
        for env in environments:
            await env.close()


async def get_current_session_count(client: BenchmarkPlato, agent_type: str, testcase_id: str, simulator_name: str) -> int:
    """Get the current number of sessions for a specific agent type and testcase.

    This function re-queries the API to get the most up-to-date session count,
    accounting for any sessions that may have been created during this run.
    """
    # Get agent artifacts for this type
    all_artifacts = await client.list_agent_artifacts()
    filtered_artifacts = filter_agent_artifacts(all_artifacts)

    if not filtered_artifacts[agent_type]:
        return 0

    # Get artifact IDs for this agent type
    artifact_ids = [artifact["id"] for artifact in filtered_artifacts[agent_type]]

    # Get simulator ID
    simulators = await client.list_simulators()
    simulator = next((s for s in simulators if s["name"] == simulator_name), None)
    if not simulator:
        return 0

    # Query sessions
    sessions = await client.list_sessions(
        simulator_ids=[str(simulator["id"])],
        agent_artifact_ids=[str(aid) for aid in artifact_ids]
    )

    # Count sessions for this specific testcase
    count = sum(1 for session in sessions if session.get("testCase", {}).get("publicId") == testcase_id)
    return count


async def main():
    """Main function to benchmark agent coverage across environments."""
    parser = argparse.ArgumentParser(description="Benchmark agent coverage across all environments")
    parser.add_argument(
        "--simulator",
        type=str,
        default=None,
        help="Simulator name to benchmark (if not specified, will benchmark all simulators)",
        required=False,
    )
    parser.add_argument(
        "--target-sessions",
        type=int,
        default=3,
        help="Target number of sessions per agent type per test case (default: 5)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent sessions to run (default: 5)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only analyze current coverage without creating new sessions",
    )
    args = parser.parse_args()

    client = BenchmarkPlato(api_key=PLATO_API_KEY)

    try:
        # Get all simulators
        simulators = await client.list_simulators()

        if args.simulator:
            simulators = [s for s in simulators if s["name"] == args.simulator]
            if not simulators:
                logger.error(f"Simulator '{args.simulator}' not found")
                return

        logger.info(f"Benchmarking {len(simulators)} simulators")

        # Process each simulator
        for simulator in simulators:
            simulator_name = simulator["name"]
            simulator_id = simulator["id"]

            logger.info(f"Processing simulator: {simulator_name}")

            # Get all agent artifacts
            agent_artifacts = await client.list_agent_artifacts()
            filtered_artifacts = filter_agent_artifacts(agent_artifacts)

            # Skip if no relevant agent artifacts found
            total_artifacts = sum(len(artifacts) for artifacts in filtered_artifacts.values())
            if total_artifacts == 0:
                logger.warning(f"No relevant agent artifacts found for {simulator_name}, skipping")
                continue

            # Get all artifact IDs for this simulator
            all_artifact_ids = []
            for artifacts in filtered_artifacts.values():
                all_artifact_ids.extend([artifact["id"] for artifact in artifacts])

            # Get all sessions for this simulator and these artifacts
            sessions = await client.list_sessions(
                simulator_ids=[str(simulator_id)],
                agent_artifact_ids=[str(aid) for aid in all_artifact_ids]
            )

            logger.info(f"Found {len(sessions)} existing sessions for {simulator_name}")

            # Load test cases for this simulator
            testcases = await client.load_tasks(simulator_name)
            logger.info(f"Found {len(testcases)} test cases for {simulator_name}")

            # Count current sessions by agent type and test case
            session_counts = count_sessions_by_agent_and_testcase(sessions, filtered_artifacts)

            # Find missing sessions
            missing_sessions = find_missing_sessions(session_counts, testcases, args.target_sessions)

            # Report current coverage
            logger.info(f"Coverage report for {simulator_name}:")
            for agent_type in ["browser_use", "anthropic", "openai"]:
                total_needed = len(testcases) * args.target_sessions
                total_existing = sum(session_counts.get(agent_type, {}).values())
                missing_count = len(missing_sessions.get(agent_type, []))

                logger.info(f"  {agent_type}: {total_existing}/{total_needed} sessions "
                           f"({missing_count} test cases need more sessions)")

            # Create missing sessions if not in dry-run mode
            if not args.dry_run and any(missing_sessions.values()):
                await create_missing_sessions(
                    client, missing_sessions, testcases, simulator_name,
                    args.concurrency, args.target_sessions
                )
            elif args.dry_run:
                logger.info("Dry run mode: not creating missing sessions")
            else:
                logger.info(f"All agent types have sufficient coverage for {simulator_name}")

        logger.info("Benchmarking complete!")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
