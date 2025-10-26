#!/bin/bash

# Generate protobuf code for all languages

set -e

echo "🔧 Generating Protocol Buffer code for all languages..."
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

# Generate Go code
echo "🐹 Generating Go protobuf code..."
protoc --go_out=. --go_opt=paths=source_relative proto/plato.proto

# Generate Python code
echo "🐍 Generating Python protobuf code..."
protoc --python_out=bindings/python proto/plato.proto

# Optional: Generate JavaScript code (uncomment if needed)
# echo "📜 Generating JavaScript protobuf code..."
# protoc --js_out=import_style=commonjs,binary:bindings/javascript proto/plato.proto

echo ""
echo "✅ Protocol Buffer code generation complete!"
echo ""
echo "Generated files:"
echo "  - Go:     models/plato.pb.go"
echo "  - Python: bindings/python/plato_pb2.py"
echo ""
echo "Next steps:"
echo "  1. Run 'go mod tidy' in sdk/, bindings/c/, and cmd/plato/"
echo "  2. Build CLI: cd cmd/plato && ./build.sh"
echo "  3. Build C lib: cd bindings/c && go build -buildmode=c-shared -o libplato.dylib ."
echo ""
