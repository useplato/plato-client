#!/bin/bash

# Unified build script for Plato SDK
# Generates protobuf code and builds all components

set -e

echo "🚀 Plato SDK Build Script"
echo "=========================="
echo ""

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "❌ protoc not found. Please install protoc first."
    echo "   brew install protobuf"
    exit 1
fi

# Check if protoc-gen-go is installed
if ! command -v protoc-gen-go &> /dev/null; then
    echo "📦 Installing protoc-gen-go..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
fi

# Step 1: Generate protobuf code
echo "🔧 Step 1: Generating Protocol Buffer code..."
echo ""

echo "  🐹 Generating Go protobuf code..."
protoc --go_out=. --go_opt=paths=source_relative proto/plato.proto

echo "  🐍 Generating Python protobuf code..."
protoc --python_out=bindings/python proto/plato.proto

echo ""
echo "✅ Protobuf generation complete!"
echo ""

# Step 2: Update dependencies
echo "🔧 Step 2: Updating Go module dependencies..."
echo ""

echo "  📦 Updating root SDK dependencies..."
go mod tidy

echo "  📦 Updating C bindings dependencies..."
cd bindings/c
go mod tidy
cd ../..

echo "  📦 Updating CLI dependencies..."
cd cmd/plato
go mod tidy
cd ../..

echo ""
echo "✅ Dependencies updated!"
echo ""

# Step 3: Build everything
echo "🔧 Step 3: Building all components..."
echo ""

echo "  🐹 Building root SDK..."
go build ./...

echo "  📚 Building C bindings (libplato.dylib)..."
cd bindings/c
go build -buildmode=c-shared -o libplato.dylib .
cd ../..

echo "  🛠️  Building CLI..."
cd cmd/plato
go build .
cd ../..

echo ""
echo "✅ All builds complete!"
echo ""
echo "Generated files:"
echo "  - Go protobuf:     models/plato.pb.go"
echo "  - Python protobuf: bindings/python/plato_pb2.py"
echo "  - C library:       bindings/c/libplato.dylib"
echo "  - CLI binary:      cmd/plato/plato"
echo ""
echo "🎉 Success! Everything is built and ready to use."
echo ""
