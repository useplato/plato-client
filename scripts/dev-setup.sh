#!/usr/bin/env bash
# Setup development environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🛠️  Setting up Plato development environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Go installation
echo "Checking Go installation..."
if command -v go &> /dev/null; then
    GO_VERSION=$(go version | awk '{print $3}')
    echo "  ✅ Go installed: $GO_VERSION"
else
    echo "  ❌ Go not found"
    echo "  Please install Go 1.23+ from https://go.dev/dl/"
    exit 1
fi
echo ""

# Check Python installation
echo "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "  ✅ Python installed: $PYTHON_VERSION"
else
    echo "  ❌ Python3 not found"
    echo "  Please install Python 3.10+ from https://python.org"
    exit 1
fi
echo ""

# Check/Install uv
echo "Checking uv installation..."
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version)
    echo "  ✅ uv installed: $UV_VERSION"
else
    echo "  ⚠️  uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "  ✅ uv installed"
fi
echo ""

# Setup Go SDK
echo "Setting up Go SDK..."
cd "$PROJECT_ROOT/sdk"
go mod download
echo "  ✅ Go dependencies installed"
echo ""

# Setup CLI
echo "Setting up CLI..."
cd "$PROJECT_ROOT/cli"
go mod download
echo "  ✅ CLI dependencies installed"
echo ""

# Setup C bindings
echo "Setting up C bindings..."
cd "$PROJECT_ROOT/sdk/bindings/c"
if [ ! -f "go.mod" ]; then
    go mod init plato-bindings
    go mod edit -replace plato-sdk=../../
    go get plato-sdk
    go mod tidy
fi
echo "  ✅ C bindings module initialized"
echo ""

# Setup Python
echo "Setting up Python SDK..."
cd "$PROJECT_ROOT/python"
uv sync
echo "  ✅ Python dependencies installed"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Development environment ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  1. Build all components:"
echo "     ./scripts/build-all.sh"
echo ""
echo "  2. Or build individually:"
echo "     ./scripts/build-sdk.sh     # Go SDK"
echo "     ./scripts/build-cli.sh     # CLI tool"
echo "     ./scripts/build-python.sh  # Python SDK + C bindings"
echo ""
echo "  3. Run tests:"
echo "     ./scripts/test-sdk.sh      # Go SDK tests"
echo "     ./scripts/test-python.sh   # Python tests"
