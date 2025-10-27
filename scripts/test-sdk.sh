#!/usr/bin/env bash
# Test Plato Go SDK
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SDK_DIR="$PROJECT_ROOT/sdk"

echo "🧪 Testing Plato Go SDK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$SDK_DIR"

# Run tests with coverage
echo "Running tests with coverage..."
go test ./... -v -coverprofile=coverage.out

echo ""
echo "Coverage report:"
go tool cover -func=coverage.out | tail -n 1

echo ""
echo "To view detailed coverage:"
echo "  cd $SDK_DIR"
echo "  go tool cover -html=coverage.out"
