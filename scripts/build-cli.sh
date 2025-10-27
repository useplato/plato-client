#!/bin/bash
# Build the Plato CLI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔨 Building Plato CLI..."
echo ""

cd "$PROJECT_ROOT/cli"

# Get version info
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
LDFLAGS="-X 'plato-cli/internal/ui/components.Version=${VERSION}' -X 'plato-cli/internal/ui/components.GitCommit=${GIT_COMMIT}' -X 'plato-cli/internal/ui/components.BuildTime=${BUILD_TIME}'"

echo "   Version:    ${VERSION}"
echo "   Commit:     ${GIT_COMMIT}"
echo "   Build Time: ${BUILD_TIME}"
echo ""

# Update dependencies
echo "📦 Updating dependencies..."
go mod tidy

# Build
echo "🏗️  Building CLI binary..."
go build -ldflags "${LDFLAGS}" -o plato

echo ""
echo "✅ CLI build complete!"
echo ""
echo "Binary location: cli/plato"
echo ""
echo "To install globally:"
echo "  mkdir -p ~/.local/bin"
echo "  cp plato ~/.local/bin/plato"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
