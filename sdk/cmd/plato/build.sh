#!/bin/bash

# Build and install script for Plato CLI

set -e

# Get version from VERSION file, or default to "dev"
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION)
else
    VERSION="dev"
fi

# Get git commit hash (short form)
if git rev-parse --short HEAD >/dev/null 2>&1; then
    GIT_COMMIT=$(git rev-parse --short HEAD)
else
    GIT_COMMIT="unknown"
fi

# Get build timestamp
BUILD_TIME=$(date -u '+%Y-%m-%d_%H:%M:%S_UTC')

# Build ldflags
LDFLAGS="-X 'plato-sdk/cmd/plato/internal/ui/components.Version=${VERSION}' -X 'plato-sdk/cmd/plato/internal/ui/components.GitCommit=${GIT_COMMIT}' -X 'plato-sdk/cmd/plato/internal/ui/components.BuildTime=${BUILD_TIME}'"

echo "🔨 Building Plato CLI..."
echo "   Version:    ${VERSION}"
echo "   Commit:     ${GIT_COMMIT}"
echo "   Build Time: ${BUILD_TIME}"
echo ""

go build -ldflags "${LDFLAGS}" -o plato

echo "📦 Installing to ~/.local/bin..."
mkdir -p ~/.local/bin
cp plato ~/.local/bin/plato
chmod +x ~/.local/bin/plato

echo "✅ Plato CLI installed successfully!"
echo ""
echo "📍 Location: ~/.local/bin/plato"
echo "🚀 Run 'plato' from anywhere to start"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  Warning: ~/.local/bin is not in your PATH"
    echo "Add this to your ~/.zshrc or ~/.bashrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi
