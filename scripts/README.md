# Plato Build Scripts

Automated build and development scripts for the Plato SDK project.

## Quick Start

```bash
# Setup development environment (first time only)
./scripts/dev-setup.sh

# Build everything
./scripts/build-all.sh

# Or build individually
./scripts/build-sdk.sh     # Go SDK
./scripts/build-cli.sh     # CLI tool
./scripts/build-python.sh  # Python SDK with C bindings
```

## Available Scripts

### Setup & Development

#### `dev-setup.sh`
Setup the complete development environment.

- Checks for required tools (Go, Python, uv)
- Installs missing tools (uv)
- Initializes all Go modules
- Installs Python dependencies

**Usage:**
```bash
./scripts/dev-setup.sh
```

**First time setup:**
1. Install Go 1.23+ from https://go.dev/dl/
2. Install Python 3.10+ from https://python.org
3. Run `./scripts/dev-setup.sh`

---

### Build Scripts

#### `build-all.sh`
Build all components in order: SDK → CLI → Python.

**Usage:**
```bash
./scripts/build-all.sh
```

**Output:**
- SDK: Verified and tested
- CLI: Binary in `cli/bin/plato`
- Python: Wheel in `python/dist/`

---

#### `build-sdk.sh`
Build and test the Go SDK.

**What it does:**
1. Syncs Go dependencies (`go mod tidy`)
2. Runs all tests
3. Verifies SDK builds

**Usage:**
```bash
./scripts/build-sdk.sh
```

**Output:**
- Go SDK ready for use by CLI and Python bindings
- Test results displayed

---

#### `build-cli.sh`
Build the Plato CLI binary.

**What it does:**
1. Syncs Go dependencies
2. Builds CLI binary
3. Tests the binary (`plato --version`)

**Usage:**
```bash
./scripts/build-cli.sh
```

**Output:**
- Binary: `cli/bin/plato` (or `plato.exe` on Windows)
- Install instructions displayed

**Install globally:**
```bash
sudo cp cli/bin/plato /usr/local/bin/
```

---

#### `build-python.sh`
Build the Python SDK with C bindings.

**What it does:**
1. Builds C shared library from Go code (`libplato.dylib/so/dll`)
2. Copies library to Python package (`python/src/plato/`)
3. Builds Python wheel distribution

**Usage:**
```bash
./scripts/build-python.sh
```

**Output:**
- C library: `sdk/bindings/c/libplato.dylib` (or `.so`/`.dll`)
- Package library: `python/src/plato/libplato.dylib`
- Python wheel: `python/dist/plato_sdk-*.whl`

**Install locally:**
```bash
cd python
uv pip install -e .
```

**Publish to PyPI:**
```bash
cd python
uv publish
```

---

### Test Scripts

#### `test-sdk.sh`
Run Go SDK tests with coverage.

**Usage:**
```bash
./scripts/test-sdk.sh
```

**Output:**
- Test results
- Coverage report
- `sdk/coverage.out` file

**View detailed coverage:**
```bash
cd sdk
go tool cover -html=coverage.out
```

---

#### `test-python.sh`
Run Python SDK tests.

**What it does:**
1. Checks if C library exists (builds if needed)
2. Runs pytest tests if available
3. Runs example test scripts

**Usage:**
```bash
./scripts/test-python.sh
```

**Requirements:**
- C library must be built first (script builds automatically if missing)
- Tests in `python/tests/` or `python/test_*.py`

---

### Utility Scripts

#### `retag_wheel.py`
Retag Python wheels with correct platform-specific tags.

**What it does:**
1. Parses wheel filename to extract metadata
2. Updates internal WHEEL metadata file
3. Renames wheel file with correct platform tag
4. Used for cross-compiled builds in CI/CD

**Usage:**
```bash
cd python
python ../scripts/retag_wheel.py <platform> [dist_dir]
```

**Platforms:**
- `linux-amd64` → `manylinux_2_17_x86_64.manylinux2014_x86_64`
- `linux-arm64` → `manylinux_2_17_aarch64.manylinux2014_aarch64`
- `macos-x86_64` → `macosx_10_9_x86_64`
- `macos-arm64` → `macosx_11_0_arm64`

**Example:**
```bash
# Build a wheel
cd python
python -m build --wheel

# Retag it for Linux ARM64
python ../scripts/retag_wheel.py linux-arm64

# Result: plato_sdk-1.1.20-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
```

**Use Case:**
This script is essential for cross-compilation scenarios where the build
platform differs from the target platform. For example, building ARM64
wheels on an x86_64 GitHub Actions runner.

---

#### `clean.sh`
Remove all build artifacts and caches.

**What it cleans:**
- Go build caches and coverage files
- C shared libraries (`libplato.*`)
- CLI binaries (`cli/bin/`)
- Python dist, build, egg-info, `__pycache__`
- Python package libraries (`python/src/plato/libplato.*`)

**Usage:**
```bash
./scripts/clean.sh
```

**Note:** Does not remove dependencies (Go modules, Python packages)

---

## Architecture

The build scripts follow this dependency order:

```
┌─────────────┐
│   Go SDK    │  (Core SDK)
└──────┬──────┘
       │
       ├────────────────┬────────────────┐
       ▼                ▼                ▼
┌──────────┐     ┌──────────┐    ┌──────────┐
│   CLI    │     │ C Bindings│    │  Future  │
└──────────┘     └─────┬─────┘    └──────────┘
                       │
                       ▼
                 ┌──────────┐
                 │  Python  │
                 └──────────┘
```

1. **Go SDK** (`sdk/`): Core SDK with services and models
2. **CLI** (`cli/`): Command-line tool using Go SDK
3. **C Bindings** (`sdk/bindings/c/`): cgo exports for foreign language support
4. **Python SDK** (`python/`): Python wrapper using C bindings via ctypes

## Common Workflows

### Development Workflow

```bash
# First time setup
./scripts/dev-setup.sh

# Make changes to SDK
cd sdk
# ... edit code ...

# Test your changes
./scripts/test-sdk.sh

# Build CLI with your changes
./scripts/build-cli.sh

# Test CLI
./cli/bin/plato --version
```

### Python Development Workflow

```bash
# Make changes to Go SDK or C bindings
cd sdk
# ... edit code ...

# Rebuild Python bindings
./scripts/build-python.sh

# Test Python SDK
cd python
uv run python3 test_full_workflow.py
```

### Release Workflow

```bash
# Clean everything
./scripts/clean.sh

# Fresh build
./scripts/build-all.sh

# If all builds succeed, tag and push
git tag v1.0.94
git push origin v1.0.94

# GitHub Actions will automatically:
# 1. Build CLI for multiple platforms
# 2. Build Python SDK with C bindings
# 3. Publish to PyPI
```

## Troubleshooting

### "Go not found"
Install Go 1.23+ from https://go.dev/dl/

### "Python3 not found"
Install Python 3.10+ from https://python.org

### "uv not found"
Run: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### "libplato not found" (Python)
The C library wasn't built. Run:
```bash
./scripts/build-python.sh
```

### Build fails with "cannot find module"
Run dev setup again:
```bash
./scripts/dev-setup.sh
```

### Tests fail
Make sure dependencies are installed:
```bash
cd sdk && go mod download
cd python && uv sync
```

## Platform Notes

### macOS
- C library: `libplato.dylib`
- CLI binary: `plato`

### Linux
- C library: `libplato.so`
- CLI binary: `plato`

### Windows
- C library: `libplato.dll`
- CLI binary: `plato.exe`

All scripts detect the platform automatically.

## Contributing

When adding new build steps:

1. Add the step to the appropriate script
2. Update this README
3. Test on all platforms (use GitHub Actions)
4. Keep scripts idempotent (safe to run multiple times)
