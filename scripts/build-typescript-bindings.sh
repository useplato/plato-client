#!/usr/bin/env bash
# Build TypeScript SDK with C bindings (reuses same library as Python)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BINDINGS_DIR="$PROJECT_ROOT/sdk/bindings/c"
JAVASCRIPT_DIR="$PROJECT_ROOT/javascript"

echo "🔨 Building Plato TypeScript SDK (Native Bindings)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 0: Generate TypeScript types from OpenAPI
echo "Step 0/4: Generating TypeScript types from OpenAPI"
echo "────────────────────────────────────────"
"$SCRIPT_DIR/generate-typescript-types.sh" || {
    echo "⚠️  Warning: Failed to generate types, continuing anyway"
}
echo ""

# Step 1: Build C shared library (same as Python)
echo "Step 1/4: Building C shared library"
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

# Step 2: Copy library to JavaScript package
echo "Step 2/5: Copying library to JavaScript package"
echo "────────────────────────────────────────"
JAVASCRIPT_SRC_DIR="$JAVASCRIPT_DIR/src/plato"
mkdir -p "$JAVASCRIPT_SRC_DIR"
cp "$LIB_NAME" "$JAVASCRIPT_SRC_DIR/"
echo "✅ Copied to $JAVASCRIPT_SRC_DIR/$LIB_NAME"
echo ""

# Step 3: Install Node.js dependencies
echo "Step 3/5: Installing Node.js dependencies"
echo "────────────────────────────────────────"
cd "$JAVASCRIPT_DIR"

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js"
    exit 1
fi

echo "📦 Installing dependencies..."
npm install
echo "✅ Dependencies installed"
echo ""

# Step 4: Build TypeScript
echo "Step 4/5: Building TypeScript"
echo "────────────────────────────────────────"
echo "📦 Compiling TypeScript..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ TypeScript compiled"
else
    echo "❌ TypeScript compilation failed"
    exit 1
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ TypeScript SDK ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "C Library: $BINDINGS_DIR/$LIB_NAME"
echo "JavaScript Package: $JAVASCRIPT_DIR/"
echo "Distribution: $JAVASCRIPT_DIR/dist/"
echo ""
echo "To test locally:"
echo "  cd $JAVASCRIPT_DIR"
echo "  npm link"
echo "  cd /path/to/your/project"
echo "  npm link plato-sdk"
echo ""
echo "To publish to NPM:"
echo "  cd $JAVASCRIPT_DIR"
echo "  npm publish"

