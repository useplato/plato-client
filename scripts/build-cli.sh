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

# Build the CLI
echo "📦 Building CLI binary..."
OUTPUT_DIR="$CLI_DIR/bin"
mkdir -p "$OUTPUT_DIR"

if go build -ldflags="${LDFLAGS}" -o "$OUTPUT_DIR/$BINARY_NAME" .; then
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
# Copy Python scripts to bin directory
echo "📦 Copying Python scripts..."
if [[ -f "$CLI_DIR/configure_ignore_tables_ui.py" ]]; then
    cp "$CLI_DIR/configure_ignore_tables_ui.py" "$OUTPUT_DIR/"
    echo "✅ Copied configure_ignore_tables_ui.py"
else
    echo "⚠️  configure_ignore_tables_ui.py not found"
fi


# Copy bundled proxytunnel binary to the same directory
echo "📦 Copying bundled proxytunnel binary..."
PROXYTUNNEL_SRC="$PROJECT_ROOT/python/src/plato/bin"
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ "$(uname -m)" == "arm64" ]]; then
        PROXYTUNNEL_NAME="proxytunnel-darwin-arm64"
    else
        PROXYTUNNEL_NAME="proxytunnel-darwin-amd64"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [[ "$(uname -m)" == "aarch64" ]] || [[ "$(uname -m)" == "arm64" ]]; then
        PROXYTUNNEL_NAME="proxytunnel-linux-arm64"
    else
        PROXYTUNNEL_NAME="proxytunnel-linux-amd64"
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    PROXYTUNNEL_NAME="proxytunnel.exe"
else
    echo "⚠️  Unknown platform, skipping proxytunnel copy"
    PROXYTUNNEL_NAME=""
fi

if [[ -n "$PROXYTUNNEL_NAME" ]]; then
    if [[ -f "$PROXYTUNNEL_SRC/$PROXYTUNNEL_NAME" ]]; then
        cp "$PROXYTUNNEL_SRC/$PROXYTUNNEL_NAME" "$OUTPUT_DIR/"
        chmod +x "$OUTPUT_DIR/$PROXYTUNNEL_NAME"
        echo "✅ Copied $PROXYTUNNEL_NAME to $OUTPUT_DIR"
    else
        echo "⚠️  Proxytunnel binary not found at $PROXYTUNNEL_SRC/$PROXYTUNNEL_NAME"
        echo "    Run ./scripts/build-proxytunnel.sh first"
    fi
fi
echo ""

# Test the binary
echo "🧪 Testing binary..."
if "$OUTPUT_DIR/$BINARY_NAME" --version; then
    echo "✅ Binary works"
else
    echo "❌ Binary test failed"
    exit 1
fi
echo ""

# Copy to Python package bin directory for integration with Python SDK
echo "📦 Copying CLI to Python package..."
PYTHON_BIN_DIR="$PROJECT_ROOT/python/src/plato/bin"
mkdir -p "$PYTHON_BIN_DIR"

# Copy with the name expected by the Python CLI wrapper
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    PYTHON_BINARY_NAME="plato-cli.exe"
else
    PYTHON_BINARY_NAME="plato-cli"
fi

cp "$OUTPUT_DIR/$BINARY_NAME" "$PYTHON_BIN_DIR/$PYTHON_BINARY_NAME"
chmod +x "$PYTHON_BIN_DIR/$PYTHON_BINARY_NAME"
echo "✅ Copied to $PYTHON_BIN_DIR/$PYTHON_BINARY_NAME"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ CLI ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Binary: $OUTPUT_DIR/$BINARY_NAME"
echo "Python package: $PYTHON_BIN_DIR/$PYTHON_BINARY_NAME"
echo ""
echo "To install globally:"
echo "  sudo cp $OUTPUT_DIR/$BINARY_NAME /usr/local/bin/"
echo ""
echo "Or add to PATH:"
echo "  export PATH=\"$OUTPUT_DIR:\$PATH\""
echo ""
echo "To update Python package with new CLI:"
echo "  cd python && uv pip install -e . --force-reinstall --no-deps"
