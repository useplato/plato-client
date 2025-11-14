#!/bin/bash
set -e

# Build TypeScript SDK with Fern while preserving custom helper files
# This script ensures that custom business logic in the helpers/ directory
# is not overwritten during SDK regeneration.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SDK_DIR="$PROJECT_ROOT/sdk"
FERN_DIR="$SDK_DIR/fern"
TS_SDK_DIR="$SDK_DIR/sdks/typescript"
HELPERS_DIR="$TS_SDK_DIR/helpers"
BACKUP_DIR="/tmp/plato-ts-sdk-helpers-backup-$$"

echo "🚀 Building TypeScript SDK with Fern..."
echo "📁 Project root: $PROJECT_ROOT"
echo "📁 SDK directory: $TS_SDK_DIR"

# Step 1: Backup custom helpers
if [ -d "$HELPERS_DIR" ]; then
  echo "📦 Backing up custom helpers to $BACKUP_DIR..."
  mkdir -p "$BACKUP_DIR"
  cp -r "$HELPERS_DIR" "$BACKUP_DIR/"
  echo "✅ Backup complete"
else
  echo "⚠️  No helpers directory found at $HELPERS_DIR"
  echo "   Skipping backup..."
fi

# Step 2: Generate SDK with Fern
echo ""
echo "🔨 Running Fern generation..."
cd "$FERN_DIR"

if ! command -v fern &> /dev/null; then
  echo "❌ Error: fern CLI not found"
  echo "   Install it with: npm install -g fern-api"
  exit 1
fi

fern generate --group local

echo "✅ Fern generation complete"

# Step 3: Restore custom helpers
if [ -d "$BACKUP_DIR/helpers" ]; then
  echo ""
  echo "🔄 Restoring custom helpers..."
  rm -rf "$HELPERS_DIR"
  cp -r "$BACKUP_DIR/helpers" "$TS_SDK_DIR/"
  echo "✅ Custom helpers restored"
  
  # Cleanup backup
  rm -rf "$BACKUP_DIR"
  echo "🧹 Cleaned up temporary backup"
else
  echo "⚠️  No backup found, skipping restore"
fi

# Step 4: Install dependencies if needed
echo ""
echo "📦 Installing TypeScript SDK dependencies..."
cd "$TS_SDK_DIR"

if [ -f "package.json" ]; then
  if command -v npm &> /dev/null; then
    npm install
    echo "✅ Dependencies installed"
  else
    echo "⚠️  npm not found, skipping dependency installation"
  fi
fi

echo ""
echo "✨ TypeScript SDK build complete!"
echo "📍 SDK location: $TS_SDK_DIR"
echo ""
echo "Custom files preserved:"
echo "  - helpers/SandboxMonitor.ts"
echo "  - helpers/SandboxHelpers.ts"
echo "  - helpers/index.ts"
echo "  - helpers/README.md"

