#!/usr/bin/env python3
"""
Simple example showing how to use the database tunnel feature.

This example demonstrates:
1. Creating a Plato environment
2. Starting a database tunnel
3. Connecting to the database via the tunnel
4. Stopping the tunnel when done
"""

import argparse
import asyncio

from plato.sdk import Plato


async def main():
    parser = argparse.ArgumentParser(description="Database tunnel example")
    parser.add_argument("-s", "--simulator", required=True, help="Simulator name")
    parser.add_argument(
        "-e", "--env", default="prod", help="Environment (prod/staging)"
    )
    args = parser.parse_args()

    # Initialize client
    base_url = f"https://{'plato.so' if args.env == 'prod' else 'staging.plato.so'}/api"
    client = Plato(base_url=base_url)

    try:
        # Create environment
        print(f"📦 Creating environment for {args.simulator}...")
        env = await client.make_environment(
            env_id=args.simulator,
            dataset="base",
            interface_type=None,
        )
        print(f"✅ Environment created: {env.id}")
        print(f"🌐 Public URL: {await env.get_public_url()}")

        # Wait for environment to be ready
        print("\n⏳ Waiting for environment to be ready...")
        await env.wait_for_ready()
        print("✅ Environment is ready")

        # Reset to get a run session
        print("🔄 Resetting environment...")
        await env.reset()
        print("✅ Environment reset complete")

        # Get DB login info
        login = env.get_db_login_info()
        print(f"\n📊 Database Info:")
        print(f"  Type: {login['db_type']}")
        print(f"  User: {login['user']}")
        databases = login.get("databases", [])
        if databases:
            print(f"  Available databases: {', '.join(databases)}")
        else:
            print(f"  Available databases: Unknown")

        # Start DB tunnel
        print(f"\n🔌 Starting database tunnel...")
        local_port = await env.start_db_tunnel()
        print(f"✅ Tunnel started on local port: {local_port}")

        # Show connection string
        scheme = "postgresql" if login["db_type"] == "postgresql" else "mysql"
        databases = login.get("databases", [])
        if databases:
            # Show connection for non-system databases
            app_dbs = [
                db
                for db in databases
                if db not in ("postgres", "template0", "template1")
            ]
            if app_dbs:
                db_name = app_dbs[0]
                print(f"\n📝 Example connection string:")
                print(
                    f"  {scheme}://{login['user']}:{login['password']}@127.0.0.1:{local_port}/{db_name}"
                )

        print(f"\n💡 You can now connect to the database using:")
        if login["db_type"] == "postgresql":
            print(f"  psql -h 127.0.0.1 -p {local_port} -U {login['user']}")
        else:
            print(f"  mysql -h 127.0.0.1 -P {local_port} -u {login['user']} -p")

        print("\n⏸️  Press Ctrl+C to stop the tunnel...")
        # Keep tunnel open until interrupted
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping...")
    finally:
        # Stop DB tunnel
        if hasattr(env, "stop_db_tunnel"):
            env.stop_db_tunnel()
            print("✅ Database tunnel stopped")


if __name__ == "__main__":
    asyncio.run(main())
