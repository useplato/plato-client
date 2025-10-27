#!/usr/bin/env bash
# Build Python bindings for Plato SDK
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BINDINGS_DIR="$PROJECT_ROOT/sdk/bindings"

echo "🔨 Building Plato Python Bindings..."
echo ""

# Build C shared library
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Building C shared library"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$BINDINGS_DIR/c"

# Initialize Go module if needed
if [ ! -f "go.mod" ]; then
    echo "📦 Initializing Go module..."
    go mod init plato-bindings
    go mod edit -replace plato-sdk=../../
    go get plato-sdk
    go mod tidy
fi

# Detect platform and set library name
if [[ "$OSTYPE" == "darwin"* ]]; then
    LIB_NAME="libplato.dylib"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LIB_NAME="libplato.so"
else
    LIB_NAME="libplato.dll"
fi

echo "📦 Building $LIB_NAME..."
go build -buildmode=c-shared -o "$LIB_NAME" sandbox.go

LIB_SIZE=$(du -h "$LIB_NAME" | cut -f1)
echo "✅ Built $LIB_NAME ($LIB_SIZE)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Python bindings ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Library: $BINDINGS_DIR/c/$LIB_NAME"
echo "Python SDK: $BINDINGS_DIR/python/sandbox_sdk.py"
echo ""
echo "To use:"
echo "  cd $BINDINGS_DIR/python"
echo "  python example.py"
