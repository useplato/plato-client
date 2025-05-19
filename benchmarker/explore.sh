#!/bin/bash

# Take in args
runs=$1

# Make a for loop that does [100 * (2 ** i) for i in 0 to 10]
# for i in {0..10}; do
#     runs=$((100 * (2 ** i)))
#     uv run main.py --simulator craigslist --task-name specialized_equipment_purchase --runs $runs --concurrency 1 --agent browser_use --record-network-requests true --passthrough true
# done

# Run the benchmarker with the given arguments
uv run main.py --simulator craigslist --task-name specialized_equipment_purchase --runs $runs --concurrency 1 --agent browser_use --record-network-requests true --passthrough true

