#!/usr/bin/env bash
# Test Plato Python SDK
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_DIR="$PROJECT_ROOT/python"

echo "🧪 Testing Plato Python SDK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$PYTHON_DIR"

# Check if library exists
LIB_PATH="src/plato/libplato.dylib"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LIB_PATH="src/plato/libplato.so"
fi

if [ ! -f "$LIB_PATH" ]; then
    echo "⚠️  C library not found. Building first..."
    "$SCRIPT_DIR/build-python.sh"
    echo ""
fi

# Run Python tests
echo "Running Python SDK tests..."
if [ -f "tests/test_sandbox.py" ]; then
    uv run pytest tests/ -v
else
    echo "No pytest tests found, running example scripts..."

    # Run any test_*.py files
    for test_file in test_*.py; do
        if [ -f "$test_file" ]; then
            echo "Running $test_file..."
            uv run python3 "$test_file"
            echo ""
        fi
    done
fi

echo "✅ Tests completed"
