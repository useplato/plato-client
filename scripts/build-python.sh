#!/usr/bin/env bash
# Build Plato Python SDK with C bindings
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BINDINGS_DIR="$PROJECT_ROOT/sdk/bindings/c"
PYTHON_DIR="$PROJECT_ROOT/python"

echo "🔨 Building Plato Python SDK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Build C shared library
echo "Step 1/3: Building C shared library"
echo "────────────────────────────────────────"
cd "$BINDINGS_DIR"

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
if go build -buildmode=c-shared -o "$LIB_NAME" sandbox.go; then
    LIB_SIZE=$(du -h "$LIB_NAME" | cut -f1)
    echo "✅ Built $LIB_NAME ($LIB_SIZE)"
else
    echo "❌ Build failed"
    exit 1
fi
echo ""

# Step 2: Copy library to Python package
echo "Step 2/3: Copying library to Python package"
echo "────────────────────────────────────────"
PYTHON_PKG_DIR="$PYTHON_DIR/src/plato"
cp "$LIB_NAME" "$PYTHON_PKG_DIR/"
echo "✅ Copied to $PYTHON_PKG_DIR/$LIB_NAME"
echo ""

# Step 3: Build Python package
echo "Step 3/3: Building Python package"
echo "────────────────────────────────────────"
cd "$PYTHON_DIR"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "📦 Building Python wheel..."
if uv build; then
    echo "✅ Python package built"

    # Show built files
    if [ -d "dist" ]; then
        echo ""
        echo "Built packages:"
        ls -lh dist/ | tail -n +2 | awk '{print "  - " $9 " (" $5 ")"}'
    fi
else
    echo "❌ Build failed"
    exit 1
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Python SDK ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "C Library: $BINDINGS_DIR/$LIB_NAME"
echo "Python Package: $PYTHON_PKG_DIR/$LIB_NAME"
echo "Distribution: $PYTHON_DIR/dist/"
echo ""
echo "To install locally:"
echo "  cd $PYTHON_DIR"
echo "  uv pip install -e ."
echo ""
echo "To publish to PyPI:"
echo "  cd $PYTHON_DIR"
echo "  uv publish"
