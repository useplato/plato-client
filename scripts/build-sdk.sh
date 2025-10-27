#!/usr/bin/env bash
# Build Plato Go SDK
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SDK_DIR="$PROJECT_ROOT/sdk"

echo "🔨 Building Plato Go SDK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$SDK_DIR"

# Initialize/update Go module
echo "📦 Syncing Go dependencies..."
go mod tidy
echo "✅ Dependencies synced"
echo ""

# Run tests
echo "🧪 Running tests..."
if go test ./... -v; then
    echo "✅ All tests passed"
else
    echo "❌ Tests failed"
    exit 1
fi
echo ""

# Build the SDK (verification build)
echo "📦 Verifying SDK builds..."
if go build ./...; then
    echo "✅ SDK build successful"
else
    echo "❌ Build failed"
    exit 1
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ SDK ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Location: $SDK_DIR"
echo ""
echo "The SDK can now be used by:"
echo "  - CLI (via Go modules)"
echo "  - Python bindings (via C bindings)"
echo "  - JavaScript/TypeScript (future)"
