#!/usr/bin/env bash
# Generate TypeScript types from OpenAPI schema
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OPENAPI_FILE="$PROJECT_ROOT/sdk/openapi/plato.yaml"
OUTPUT_FILE="$PROJECT_ROOT/javascript/src/generated/types.ts"

echo "🔨 Generating TypeScript types from OpenAPI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "OpenAPI spec: $OPENAPI_FILE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Create output directory
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Check if openapi-typescript is installed globally
if ! command -v openapi-typescript &> /dev/null; then
    echo "📦 Installing openapi-typescript globally..."
    npm install -g openapi-typescript
    echo ""
fi

# Generate types
echo "📝 Generating types..."
openapi-typescript "$OPENAPI_FILE" \
  --output "$OUTPUT_FILE" \
  --additional-properties \
  --export-type \
  --alphabetize

if [ $? -eq 0 ]; then
    echo "✅ Types generated successfully"
    
    # Show file size
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo "   File: $OUTPUT_FILE ($FILE_SIZE)"
    
    # Show line count
    LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
    echo "   Lines: $LINE_COUNT"
    
    # Show a preview
    echo ""
    echo "Preview (first 30 lines):"
    echo "─────────────────────────────────────────"
    head -n 30 "$OUTPUT_FILE"
    echo "─────────────────────────────────────────"
else
    echo "❌ Type generation failed"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ TypeScript types ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Import in your code:"
echo "  import type { components } from './generated/types';"
echo "  type SimConfigDataset = components['schemas']['SimConfigDataset'];"

