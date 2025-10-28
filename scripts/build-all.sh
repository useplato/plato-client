#!/usr/bin/env bash
# Build all Plato components
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Building All Plato Components"
echo "═════════════════════════════════════════"
echo ""

# Track build status
BUILD_STATUS=()

# Build SDK
echo "━━━ 1/3: Go SDK ━━━"
if "$SCRIPT_DIR/build-sdk.sh"; then
    BUILD_STATUS+=("✅ SDK")
else
    BUILD_STATUS+=("❌ SDK")
    FAILED=1
fi
echo ""

# Build CLI
echo "━━━ 2/3: CLI ━━━"
if "$SCRIPT_DIR/build-cli.sh"; then
    BUILD_STATUS+=("✅ CLI")
else
    BUILD_STATUS+=("❌ CLI")
    FAILED=1
fi
echo ""

# Build Python
echo "━━━ 3/3: Python SDK ━━━"
if "$SCRIPT_DIR/build-python.sh"; then
    BUILD_STATUS+=("✅ Python")
else
    BUILD_STATUS+=("❌ Python")
    FAILED=1
fi
echo ""

# Summary
echo "═════════════════════════════════════════"
echo "Build Summary"
echo "═════════════════════════════════════════"
for status in "${BUILD_STATUS[@]}"; do
    echo "$status"
done
echo ""

if [ "${FAILED:-0}" = "1" ]; then
    echo "❌ Some builds failed"
    exit 1
else
    echo "✨ All builds successful!"
fi
