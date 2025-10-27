#!/usr/bin/env uv run python
"""
Load flow scripts from YAML files into the database.
Updates all rows in the artifacts table matching each simulator name.

Usage with uv:
    uv run --with psycopg2-binary --with pyyaml python load_flows_to_db.py
    uv run --with psycopg2-binary --with pyyaml python load_flows_to_db.py --dry-run
    uv run --with psycopg2-binary --with pyyaml python load_flows_to_db.py --execute
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

try:
    import yaml
except ImportError:
    print("Error: PyYAML not found. Install with: uv add pyyaml")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 not found. Install with: uv add psycopg2-binary")
    sys.exit(1)

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5445,
    "user": "postgres",
    "password": "Op4SZIt_f|eM5?ErRkWly?4GOzgJW^xR",
    "database": "postgres",
}


def load_flow_data(scripts_file: Path) -> Dict[str, Any]:
    """Load and parse a YAML flow file."""
    try:
        with open(scripts_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {scripts_file}: {e}")
        return None


def get_simulator_flows() -> Dict[str, Dict[str, Any]]:
    """Scan flows directory and collect all simulator flow data."""
    flows_dir = Path(__file__).parent
    simulator_flows = {}

    print("Scanning for flow files...")

    for item in flows_dir.iterdir():
        if item.is_dir() and item.name != "__pycache__":
            scripts_file = item / "scripts.yaml"
            if scripts_file.exists():
                flow_data = load_flow_data(scripts_file)
                if flow_data:
                    simulator_flows[item.name] = flow_data
                    print(f"  Found flows for: {item.name}")

    print(f"Total simulators with flows: {len(simulator_flows)}")
    return simulator_flows


def preview_changes(simulator_flows: Dict[str, Dict[str, Any]]) -> None:
    """Preview what changes will be made to the database."""
    print("\n" + "=" * 60)
    print("PREVIEW OF CHANGES")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Get current state of simulator_artifacts table
        cursor.execute(
            "SELECT simulator_name, COUNT(*) FROM simulator_artifacts GROUP BY simulator_name ORDER BY simulator_name"
        )
        db_simulators = dict(cursor.fetchall())

        print(f"\nSimulators in database: {len(db_simulators)}")
        print(f"Simulators with flow files: {len(simulator_flows)}")

        print(f"\nMatching simulators (will be updated):")
        matching = 0
        total_rows = 0
        for sim_name in sorted(simulator_flows.keys()):
            row_count = db_simulators.get(sim_name, 0)
            if row_count > 0:
                print(f"  {sim_name}: {row_count} artifacts")
                matching += 1
                total_rows += row_count

        print(f"\nSUMMARY:")
        print(f"  - {matching} simulators will be updated")
        print(f"  - {total_rows} total artifact rows will be updated")

        # Show simulators with flows but no DB rows
        no_rows = [
            sim for sim in simulator_flows.keys() if db_simulators.get(sim, 0) == 0
        ]
        if no_rows:
            print(
                f"  - {len(no_rows)} simulators have flows but no simulator_artifacts in DB"
            )

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error connecting to database: {e}")
        print(f"\nFound flow files for {len(simulator_flows)} simulators")
        print("Cannot determine database impact without connection")


def create_local_backup(cursor) -> str:
    """Create a local JSON backup of the entire simulator_artifacts table."""
    backup_filename = f"simulator_artifacts_backup_{int(time.time())}.json"

    print(f"Creating full table backup: {backup_filename}")

    # Get ALL data from simulator_artifacts table
    cursor.execute("SELECT * FROM simulator_artifacts ORDER BY id")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    # Convert to list of dictionaries
    backup_data = []
    for row in rows:
        backup_data.append(dict(zip(columns, row)))

    # Write to local JSON file
    with open(backup_filename, "w") as f:
        json.dump(backup_data, f, indent=2, default=str)

    print(f"Backed up {len(backup_data)} total artifacts to {backup_filename}")
    return backup_filename


def update_database(
    simulator_flows: Dict[str, Dict[str, Any]], dry_run: bool = True
) -> None:
    """Update the database with flow data."""
    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No changes will be made")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("UPDATING DATABASE")
        print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        backup_filename = None
        updated_artifacts = []
        total_updated = 0

        if not dry_run:
            # Create local backup file before making changes
            backup_filename = create_local_backup(cursor)

        for simulator_name, flow_data in simulator_flows.items():
            # Convert flow data back to YAML string
            flow_yaml = yaml.dump(flow_data, default_flow_style=False, sort_keys=False)

            if dry_run:
                # Just check how many rows would be affected
                cursor.execute(
                    "SELECT COUNT(*) FROM simulator_artifacts WHERE simulator_name = %s",
                    (simulator_name,),
                )
                row_count = cursor.fetchone()[0]
                print(f"  {simulator_name}: would update {row_count} rows")
                total_updated += row_count
            else:
                # Get the specific artifacts that will be updated
                cursor.execute(
                    "SELECT id, public_id, simulator_name, dataset FROM simulator_artifacts WHERE simulator_name = %s",
                    (simulator_name,),
                )
                artifacts = cursor.fetchall()

                # Actually update the database
                cursor.execute(
                    """
                    UPDATE simulator_artifacts 
                    SET flows = %s
                    WHERE simulator_name = %s
                """,
                    (flow_yaml, simulator_name),
                )

                updated_count = cursor.rowcount
                total_updated += updated_count

                # Log each updated artifact
                for artifact in artifacts:
                    updated_artifacts.append(
                        {
                            "id": artifact[0],
                            "public_id": artifact[1],
                            "simulator_name": artifact[2],
                            "dataset": artifact[3],
                        }
                    )

                print(f"  {simulator_name}: updated {updated_count} rows")

        if dry_run:
            print(f"\nTotal rows that would be updated: {total_updated}")
        else:
            conn.commit()
            print(f"\nTotal rows updated: {total_updated}")
            print("✓ Changes committed to database")

            # Save detailed log of updated artifacts
            log_filename = f"updated_artifacts_{int(time.time())}.json"
            with open(log_filename, "w") as f:
                json.dump(updated_artifacts, f, indent=2)

            print(f"\n📋 BACKUP INFO:")
            print(f"  - Full table backed up to: {backup_filename}")
            print(f"  - Updated artifacts logged to: {log_filename}")
            print(f"  - Total artifacts updated: {len(updated_artifacts)}")

            print(f"\n🔄 TO REVERT:")
            print(
                f"  Use the backup file {backup_filename} to restore the entire table if needed"
            )

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error updating database: {e}")
        if not dry_run:
            try:
                conn.rollback()
                print("✓ Changes rolled back")
            except:
                pass


def main():
    print("Flow Data Loader")
    print("================")

    # Load all flow data
    simulator_flows = get_simulator_flows()

    if not simulator_flows:
        print("No flow files found!")
        return

    # Show preview
    preview_changes(simulator_flows)

    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dry-run":
            update_database(simulator_flows, dry_run=True)
        elif sys.argv[1] == "--execute":
            print("\n⚠ WARNING: This will modify the database!")
            confirm = input("Type 'YES' to confirm: ")
            if confirm == "YES":
                update_database(simulator_flows, dry_run=False)
            else:
                print("Cancelled.")
        else:
            print(
                "Usage: uv run --with psycopg2-binary --with pyyaml python load_flows_to_db.py [--dry-run|--execute]"
            )
    else:
        # Auto-run dry-run to show what would happen
        print("\nRunning dry-run to show impact...")
        update_database(simulator_flows, dry_run=True)

        print("\n" + "=" * 60)
        print("To actually execute: add --execute")
        print("=" * 60)


if __name__ == "__main__":
    main()
