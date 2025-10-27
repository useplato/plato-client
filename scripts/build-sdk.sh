#!/bin/bash
# Build the Go SDK

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔨 Building Plato SDK..."
echo ""

cd "$PROJECT_ROOT/sdk"

# Update dependencies
echo "📦 Updating dependencies..."
go mod tidy

# Build
echo "🏗️  Building SDK..."
go build ./...

# Run tests
echo "🧪 Running tests..."
go test ./...

echo ""
echo "✅ SDK build complete!"
echo ""
