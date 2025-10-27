#!/bin/bash
# Generate Protocol Buffer code for all languages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Generating Protocol Buffer code..."
echo ""

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "❌ protoc not found. Please install it:"
    echo "   brew install protobuf"
    exit 1
fi

# Check if protoc-gen-go is installed
if ! command -v protoc-gen-go &> /dev/null; then
    echo "📦 Installing protoc-gen-go..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
fi

cd "$PROJECT_ROOT/sdk"

# Generate Go code
echo "🐹 Generating Go protobuf code..."
protoc --go_out=. --go_opt=paths=source_relative proto/plato.proto

echo ""
echo "✅ Protocol Buffer code generation complete!"
echo ""
echo "Generated files:"
echo "  - Go: sdk/models/plato.pb.go"
echo ""
