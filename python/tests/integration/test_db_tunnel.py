#!/usr/bin/env python3
"""
Test script to verify database tunnel functionality works for all simulators.

This script:
1. Tests a few representative simulators (PostgreSQL and MySQL)
2. Creates an environment
3. Starts a database tunnel
4. Lists databases to verify connectivity
5. Stops the tunnel
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from plato.sdk import Plato


async def test_simulator(client: Plato, sim_name: str) -> tuple[bool, str]:
    """Test DB tunnel for a single simulator."""
    try:
        print(f"\n{'=' * 80}")
        print(f"Testing: {sim_name}")
        print("=" * 80)

        # Create environment
        env = await client.make_environment(
            env_id=sim_name,
            dataset="base",
            interface_type=None,
        )
        print(f"✅ Environment created: {env.id}")

        # Wait for environment to be ready
        await env.wait_for_ready()
        print("✅ Environment is ready")

        # Reset to get a run session
        await env.reset()
        print("✅ Environment reset complete")

        # Get DB info
        login = env.get_db_login_info()
        print(f"📊 Database type: {login['db_type']}")

        # Start tunnel
        local_port = await env.start_db_tunnel()
        print(f"🔌 Tunnel started on port: {local_port}")

        # Test connection by listing databases
        try:
            if login["db_type"] == "postgresql":
                import os

                env_vars = os.environ.copy()
                env_vars["PGPASSWORD"] = login["password"]
                cmd = [
                    "psql",
                    "-h",
                    "127.0.0.1",
                    "-p",
                    str(local_port),
                    "-U",
                    login["user"],
                    "-d",
                    "postgres",
                    "-Atc",
                    "SELECT datname FROM pg_database WHERE datistemplate = false;",
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, env=env_vars
                )
            else:
                cmd = [
                    "mysql",
                    "-h",
                    "127.0.0.1",
                    "-P",
                    str(local_port),
                    "-u",
                    login["user"],
                    f"-p{login['password']}",
                    "-N",
                    "-B",
                    "-e",
                    "SHOW DATABASES;",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                databases = [d for d in result.stdout.strip().splitlines() if d]
                print(f"✅ Connection successful! Found {len(databases)} database(s)")
                print(
                    f"   Databases: {', '.join(databases[:3])}{'...' if len(databases) > 3 else ''}"
                )
            else:
                print(f"❌ Connection failed: {result.stderr.strip()}")
                return False, result.stderr.strip()
        except FileNotFoundError as e:
            client_name = "psql" if login["db_type"] == "postgresql" else "mysql"
            print(f"⚠️  {client_name} client not found - skipping connection test")
            print(f"   Tunnel started successfully on port {local_port}")
            # Don't fail the test if client is missing - tunnel still works
            pass

        # Stop tunnel
        env.stop_db_tunnel()
        print("✅ Tunnel stopped")

        return True, ""

    except Exception as e:
        return False, str(e)


async def main():
    parser = argparse.ArgumentParser(description="Test database tunnel functionality")
    parser.add_argument(
        "-e", "--env", default="prod", help="Environment (prod/staging)"
    )
    parser.add_argument(
        "-s", "--simulator", help="Specific simulator to test (optional)"
    )
    args = parser.parse_args()

    # Initialize client
    base_url = f"https://{'plato.so' if args.env == 'prod' else 'staging.plato.so'}/api"
    client = Plato(base_url=base_url)

    # Test a few representative simulators or a specific one
    if args.simulator:
        test_sims = [args.simulator]
    else:
        test_sims = [
            "espocrm",  # PostgreSQL
            "gitlab",  # PostgreSQL (large)
            "kanboard",  # MySQL
        ]

    print(f"Testing database tunnel with {len(test_sims)} simulators...")

    results = []
    for sim in test_sims:
        success, error = await test_simulator(client, sim)
        results.append((sim, success, error))

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    for sim, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {sim}")
        if error:
            print(f"       Error: {error}")

    print(f"\nTotal: {len(results)}, Passed: {passed}, Failed: {failed}")

    # Close the client session
    await client.close()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
