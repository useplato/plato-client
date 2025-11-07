#!/usr/bin/env python3
"""
Script to retag Python wheels with correct platform-specific tags.
This is used during CI/CD to ensure wheels have the correct platform tags
for cross-compiled builds.
"""

import os
import sys
import glob
import zipfile
import tempfile


def retag_wheel(wheel_path: str, target_platform: str) -> str:
    """
    Retag a wheel file with the correct platform tag.
    
    Args:
        wheel_path: Path to the wheel file
        target_platform: Target platform tag (e.g., 'manylinux_2_17_x86_64.manylinux2014_x86_64')
    
    Returns:
        Path to the retagged wheel file
    """
    wheel_name = os.path.basename(wheel_path)
    print(f"Processing wheel: {wheel_name}")
    
    # Parse wheel filename: name-version-pyver-abi-platform.whl
    # Handle package names with underscores (plato_sdk)
    parts = wheel_name[:-4].split('-')
    if len(parts) < 5:
        print(f"ERROR: Invalid wheel name format: {wheel_name}")
        sys.exit(1)
    
    # Package name might have underscores, so we need to be careful
    # Format: plato_sdk-1.1.20-cp310-cp310-linux_x86_64.whl
    # Find where version starts (first part that starts with a digit)
    version_idx = None
    for i, part in enumerate(parts):
        if part and part[0].isdigit():
            version_idx = i
            break
    
    if version_idx is None or version_idx == 0:
        print(f"ERROR: Could not find version in wheel name: {wheel_name}")
        sys.exit(1)
    
    name = '-'.join(parts[:version_idx])
    version = parts[version_idx]
    pyver = parts[version_idx + 1]
    abi = parts[version_idx + 2]
    old_platform = '-'.join(parts[version_idx + 3:])
    
    # Check if we need to fix the tag
    if target_platform in old_platform:
        print(f"✅ Wheel already has correct tag: {wheel_name}")
        return wheel_path
    
    # Create new wheel name
    new_wheel_name = f"{name}-{version}-{pyver}-{abi}-{target_platform}.whl"
    dist_dir = os.path.dirname(wheel_path)
    new_wheel_path = os.path.join(dist_dir, new_wheel_name)
    
    print("Retagging wheel:")
    print(f"  From: {old_platform}")
    print(f"  To: {target_platform}")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract wheel
        with zipfile.ZipFile(wheel_path, 'r') as zin:
            zin.extractall(tmpdir)
        
        # Find and update WHEEL metadata file
        wheel_meta = None
        for root, dirs, files in os.walk(tmpdir):
            if 'WHEEL' in files:
                wheel_meta = os.path.join(root, 'WHEEL')
                break
        
        if not wheel_meta:
            print("ERROR: Could not find WHEEL metadata file")
            sys.exit(1)
        
        # Update WHEEL file
        with open(wheel_meta, 'r') as f:
            content = f.read()
        
        # Update Tag line
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('Tag: '):
                # Parse tag: "Tag: cp310-cp310-linux_x86_64"
                tag_value = line[5:].strip()  # Remove "Tag: " prefix
                tag_parts = tag_value.split('-')
                
                if len(tag_parts) >= 3:
                    # Reconstruct tag with new platform
                    # Keep pyver and abi, replace platform
                    new_tag_value = f"{tag_parts[0]}-{tag_parts[1]}-{target_platform}"
                    new_line = f"Tag: {new_tag_value}"
                    new_lines.append(new_line)
                    print(f"  Updated tag: {new_line}")
                else:
                    # Keep original tag if we can't parse it
                    new_lines.append(line)
                    print(f"  Warning: Could not parse tag: {line}")
            else:
                new_lines.append(line)
        
        with open(wheel_meta, 'w') as f:
            f.write('\n'.join(new_lines))
        
        # Create new wheel with updated metadata
        with zipfile.ZipFile(new_wheel_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, tmpdir)
                    zout.write(file_path, arcname)
    
    # Remove old wheel
    os.remove(wheel_path)
    print(f"✅ Created new wheel: {new_wheel_name}")
    
    return new_wheel_path


def main():
    """Main entry point for the script."""
    # Define target platform tags based on the platform argument
    platform_tags = {
        "linux-amd64": "manylinux_2_17_x86_64.manylinux2014_x86_64",
        "linux-arm64": "manylinux_2_17_aarch64.manylinux2014_aarch64",
        "macos-x86_64": "macosx_10_9_x86_64",
        "macos-arm64": "macosx_11_0_arm64",
    }
    
    # Get platform from command line argument or environment
    if len(sys.argv) > 1:
        platform = sys.argv[1]
    else:
        platform = os.environ.get('PLATFORM', '')
    
    if not platform:
        print("ERROR: Platform not specified. Usage: retag_wheel.py <platform>")
        print("Valid platforms: " + ", ".join(platform_tags.keys()))
        sys.exit(1)
    
    target_tag = platform_tags.get(platform)
    if not target_tag:
        print(f"ERROR: Unknown platform '{platform}'")
        print("Valid platforms: " + ", ".join(platform_tags.keys()))
        sys.exit(1)
    
    # Find wheels in dist directory
    dist_dir = "dist"
    if len(sys.argv) > 2:
        dist_dir = sys.argv[2]
    
    wheel_pattern = os.path.join(dist_dir, "*.whl")
    wheels = glob.glob(wheel_pattern)
    
    if not wheels:
        print(f"ERROR: No wheel files found in {dist_dir}")
        sys.exit(1)
    
    print(f"Found {len(wheels)} wheel(s) to process")
    print(f"Target platform: {platform} ({target_tag})")
    print()
    
    # Process each wheel
    for wheel_path in wheels:
        retag_wheel(wheel_path, target_tag)
        print()
    
    # Show final wheels
    print("Final wheels:")
    for wheel in glob.glob(wheel_pattern):
        wheel_size = os.path.getsize(wheel)
        wheel_size_mb = wheel_size / (1024 * 1024)
        print(f"  - {os.path.basename(wheel)} ({wheel_size_mb:.2f} MB)")
    
    print()
    print("✅ All wheels retagged successfully")


if __name__ == "__main__":
    main()

