#!/usr/bin/env bash
# Build Plato CLI
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLI_DIR="$PROJECT_ROOT/cli"

echo "🔨 Building Plato CLI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$CLI_DIR"

# Initialize/update Go module
echo "📦 Syncing Go dependencies..."
go mod tidy
echo "✅ Dependencies synced"
echo ""

# Detect platform and set binary name
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    BINARY_NAME="plato.exe"
else
    BINARY_NAME="plato"
fi

# Build the CLI
echo "📦 Building CLI binary..."
OUTPUT_DIR="$CLI_DIR/bin"
mkdir -p "$OUTPUT_DIR"

if go build -o "$OUTPUT_DIR/$BINARY_NAME" .; then
    BINARY_SIZE=$(du -h "$OUTPUT_DIR/$BINARY_NAME" | cut -f1)
    echo "✅ Built $BINARY_NAME ($BINARY_SIZE)"
else
    echo "❌ Build failed"
    exit 1
fi
echo ""

# Make executable (Unix systems)
if [[ "$OSTYPE" != "msys" ]] && [[ "$OSTYPE" != "win32" ]]; then
    chmod +x "$OUTPUT_DIR/$BINARY_NAME"
fi

# Test the binary
echo "🧪 Testing binary..."
if "$OUTPUT_DIR/$BINARY_NAME" --version; then
    echo "✅ Binary works"
else
    echo "❌ Binary test failed"
    exit 1
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ CLI ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Binary: $OUTPUT_DIR/$BINARY_NAME"
echo ""
echo "To install globally:"
echo "  sudo cp $OUTPUT_DIR/$BINARY_NAME /usr/local/bin/"
echo ""
echo "Or add to PATH:"
echo "  export PATH=\"$OUTPUT_DIR:\$PATH\""
