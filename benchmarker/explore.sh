#!/bin/bash

# Take in args
runs=$1

# Run the benchmarker with the given arguments
uv run main.py --simulator craigslist --task-name find_apartment_with_criteria --runs $runs --concurrency 1 --agent browser_use --record-network-requests true

