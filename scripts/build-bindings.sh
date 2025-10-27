#!/bin/bash
# Build C bindings (shared library)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔨 Building C bindings..."
echo ""

cd "$PROJECT_ROOT/sdk/bindings/c"

# Update dependencies
echo "📦 Updating dependencies..."
go mod tidy

# Determine the library extension based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    LIB_EXT="dylib"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LIB_EXT="so"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

# Build shared library
echo "🏗️  Building shared library..."
go build -buildmode=c-shared -o "libplato.${LIB_EXT}" .

echo ""
echo "✅ C bindings build complete!"
echo ""
echo "Library location: sdk/bindings/c/libplato.${LIB_EXT}"
echo ""
