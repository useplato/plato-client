#!/bin/bash
# Generate code from Protocol Buffers for all languages

set -e

echo "Generating code from Protocol Buffers..."

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "Error: protoc not found. Install Protocol Buffers compiler:"
    echo "  macOS: brew install protobuf"
    echo "  Linux: apt-get install protobuf-compiler"
    exit 1
fi

# Generate Go code
echo "→ Generating Go code..."
protoc --go_out=.. --go_opt=paths=source_relative proto/plato.proto
echo "  ✓ Generated models/plato.pb.go"

# Generate Python code
echo "→ Generating Python code..."
protoc --python_out=../bindings/python --proto_path=. plato.proto
echo "  ✓ Generated bindings/python/plato_pb2.py"

echo "✓ All code generated successfully!"
