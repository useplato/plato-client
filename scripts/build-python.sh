#!/usr/bin/env bash
# Build Plato Python SDK with C bindings and CLI
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BINDINGS_DIR="$PROJECT_ROOT/sdk/bindings/c"
CLI_DIR="$PROJECT_ROOT/cli"
PYTHON_DIR="$PROJECT_ROOT/python"

echo "🔨 Building Plato Python SDK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 0: Build proxytunnel binary
echo "Step 0/5: Building proxytunnel binary"
echo "────────────────────────────────────────"
"$SCRIPT_DIR/build-proxytunnel.sh" || {
    echo "⚠️  Warning: Failed to build proxytunnel, continuing anyway"
}
echo ""

# Step 1: Build C shared library
echo "Step 1/5: Building C shared library"
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
echo "Step 2/5: Copying library to Python package"
echo "────────────────────────────────────────"
PYTHON_PKG_DIR="$PYTHON_DIR/src/plato"
cp "$LIB_NAME" "$PYTHON_PKG_DIR/"
echo "✅ Copied to $PYTHON_PKG_DIR/$LIB_NAME"
echo ""

# Step 3: Build CLI binary
echo "Step 3/5: Building CLI binary"
echo "────────────────────────────────────────"
cd "$CLI_DIR"

# Initialize/update Go module if needed
if [ ! -f "go.mod" ]; then
    echo "📦 Initializing Go module..."
    go mod tidy
fi

# Use a consistent binary name for the bundled CLI
BINARY_NAME="plato-cli"

# Add .exe extension for Windows
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    BINARY_NAME="plato-cli.exe"
fi

# Read version from VERSION file
VERSION="dev"
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION | tr -d '[:space:]')
    echo "📌 Version: $VERSION"
fi

# Get git commit and build time
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME=$(date -u '+%Y-%m-%d_%H:%M:%S_UTC')

# Build with version information
LDFLAGS="-X 'plato-cli/internal/ui/components.Version=${VERSION}' -X 'plato-cli/internal/ui/components.GitCommit=${GIT_COMMIT}' -X 'plato-cli/internal/ui/components.BuildTime=${BUILD_TIME}'"

echo "📦 Building CLI binary: $BINARY_NAME..."
if go build -ldflags="${LDFLAGS}" -o "$BINARY_NAME" .; then
    CLI_SIZE=$(du -h "$BINARY_NAME" | cut -f1)
    echo "✅ Built $BINARY_NAME ($CLI_SIZE)"

    # Copy to Python package
    mkdir -p "$PYTHON_PKG_DIR/bin"
    cp "$BINARY_NAME" "$PYTHON_PKG_DIR/bin/"
    chmod +x "$PYTHON_PKG_DIR/bin/$BINARY_NAME"
    echo "✅ Copied to $PYTHON_PKG_DIR/bin/$BINARY_NAME"
else
    echo "❌ CLI build failed"
    exit 1
fi
echo ""

# Step 4: Build Python package
echo "Step 4/5: Building Python package"
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
echo "CLI Binary: $PYTHON_PKG_DIR/bin/$BINARY_NAME"
echo "Python Package: $PYTHON_PKG_DIR/"
echo "Distribution: $PYTHON_DIR/dist/"
echo ""
echo "To install locally:"
echo "  cd $PYTHON_DIR"
echo "  uv pip install -e ."
echo ""
echo "To publish to PyPI:"
echo "  cd $PYTHON_DIR"
echo "  uv publish"
