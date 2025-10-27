#!/usr/bin/env python3
"""
Simple test to verify sandbox SDK can be imported and library loads
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

print("Testing Plato Sandbox SDK import...")
print()

# Test 1: Import the module
print("1. Testing import...")
try:
    from plato.sandbox_sdk import PlatoSandboxClient
    print("   ✅ Import successful")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Check library can be found
print()
print("2. Testing library discovery...")
try:
    from plato.sandbox_sdk import _find_lib
    lib_path = _find_lib()
    print(f"   ✅ Found library: {lib_path}")
except FileNotFoundError as e:
    print(f"   ❌ Library not found: {e}")
    sys.exit(1)

# Test 3: Try to load the library
print()
print("3. Testing library loading...")
try:
    from plato.sandbox_sdk import _get_lib
    lib = _get_lib()
    print("   ✅ Library loaded successfully")
except Exception as e:
    print(f"   ❌ Failed to load library: {e}")
    sys.exit(1)

# Test 4: Create a client (without API key, just to test initialization)
print()
print("4. Testing client initialization...")
try:
    client = PlatoSandboxClient('test-key')
    print(f"   ✅ Client created: {client._client_id}")
except Exception as e:
    print(f"   ❌ Client creation failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✅ All tests passed! Sandbox SDK is working.")
print("=" * 60)
