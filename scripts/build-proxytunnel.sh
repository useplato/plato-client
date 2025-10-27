#!/usr/bin/env bash
# Build proxytunnel binary for the current platform
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN_DIR="$PROJECT_ROOT/python/src/plato/bin"

# Create bin directory if it doesn't exist
mkdir -p "$PYTHON_BIN_DIR"

# Detect platform
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# Normalize architecture names
case "$ARCH" in
    x86_64|amd64)
        ARCH="amd64"
        ;;
    arm64|aarch64)
        ARCH="arm64"
        ;;
    *)
        echo "⚠️  Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

BINARY_NAME="proxytunnel-${OS}-${ARCH}"

echo "🔨 Building proxytunnel for ${OS}-${ARCH}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if proxytunnel is already available
if command -v proxytunnel &> /dev/null; then
    echo "✅ proxytunnel found in PATH, copying to package"
    cp "$(which proxytunnel)" "$PYTHON_BIN_DIR/$BINARY_NAME"
    chmod +x "$PYTHON_BIN_DIR/$BINARY_NAME"
    echo "✅ Copied to $PYTHON_BIN_DIR/$BINARY_NAME"
    exit 0
fi

# Try to install via package manager
echo "📦 Installing proxytunnel via package manager..."
if [[ "$OS" == "darwin" ]]; then
    if command -v brew &> /dev/null; then
        brew install proxytunnel || true
    fi
elif [[ "$OS" == "linux" ]]; then
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y proxytunnel || true
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y proxytunnel || true
    elif command -v yum &> /dev/null; then
        sudo yum install -y proxytunnel || true
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm proxytunnel || true
    elif command -v apk &> /dev/null; then
        sudo apk add --no-cache proxytunnel || true
    fi
fi

# Check again after installation attempt
if command -v proxytunnel &> /dev/null; then
    echo "✅ proxytunnel installed, copying to package"
    cp "$(which proxytunnel)" "$PYTHON_BIN_DIR/$BINARY_NAME"
    chmod +x "$PYTHON_BIN_DIR/$BINARY_NAME"
    echo "✅ Copied to $PYTHON_BIN_DIR/$BINARY_NAME"
    exit 0
fi

# If still not found, try building from source
echo "📦 Building proxytunnel from source..."
BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

cd "$BUILD_DIR"
git clone --depth 1 https://github.com/proxytunnel/proxytunnel.git || {
    echo "❌ Failed to clone proxytunnel repository"
    exit 1
}

cd proxytunnel
make || {
    echo "❌ Failed to build proxytunnel"
    exit 1
}

if [ ! -f "proxytunnel" ]; then
    echo "❌ proxytunnel binary not found after build"
    exit 1
fi

# Copy to package
cp proxytunnel "$PYTHON_BIN_DIR/$BINARY_NAME"
chmod +x "$PYTHON_BIN_DIR/$BINARY_NAME"
echo "✅ Built and copied to $PYTHON_BIN_DIR/$BINARY_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
