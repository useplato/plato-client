#!/usr/bin/env bash
# Clean build artifacts
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🧹 Cleaning build artifacts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Clean Go SDK
echo "Cleaning Go SDK..."
cd "$PROJECT_ROOT/sdk"
go clean -cache -testcache
if [ -f "coverage.out" ]; then
    rm coverage.out
    echo "  ✓ Removed coverage.out"
fi

# Clean C bindings
echo "Cleaning C bindings..."
cd "$PROJECT_ROOT/sdk/bindings/c"
rm -f libplato.dylib libplato.so libplato.dll libplato.h
echo "  ✓ Removed libplato.*"

# Clean CLI
echo "Cleaning CLI..."
cd "$PROJECT_ROOT/cli"
rm -rf bin/
echo "  ✓ Removed bin/"

# Clean Python
echo "Cleaning Python..."
cd "$PROJECT_ROOT/python"
rm -rf dist/ build/ *.egg-info .pytest_cache
rm -f src/plato/libplato.dylib src/plato/libplato.so src/plato/libplato.dll
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
echo "  ✓ Removed dist/, build/, *.egg-info"
echo "  ✓ Removed src/plato/libplato.*"
echo "  ✓ Removed __pycache__"

echo ""
echo "✨ Clean complete!"
