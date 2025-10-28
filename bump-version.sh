#!/bin/bash
# Bump version across all SDKs

set -e

if [ -z "$1" ]; then
    echo "Usage: ./bump-version.sh <new-version>"
    echo "Example: ./bump-version.sh 1.2.0"
    exit 1
fi

NEW_VERSION="$1"

echo "Bumping version to $NEW_VERSION..."

# Update VERSION file
echo "$NEW_VERSION" > VERSION
echo "✓ Updated VERSION file"

# Sync JavaScript
if [ -f "javascript/sync-version.js" ]; then
    cd javascript && node sync-version.js && cd ..
else
    echo "⚠️  JavaScript sync script not found"
fi

# Python version is read dynamically from VERSION file, so no action needed
echo "✓ Python will read version from VERSION file"

echo ""
echo "Version bumped to $NEW_VERSION"
echo ""
echo "To commit:"
echo "  git add VERSION python/pyproject.toml javascript/package.json"
echo "  git commit -m \"chore: bump version to $NEW_VERSION\""
