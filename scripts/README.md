# Build Scripts

Organized build scripts for the Plato client project.

## Quick Start

```bash
# Build everything (proto + SDK + bindings + CLI)
./scripts/build-all.sh

# Or build individual components
./scripts/generate-proto.sh  # Generate protobuf code
./scripts/build-sdk.sh       # Build Go SDK
./scripts/build-bindings.sh  # Build C shared library
./scripts/build-cli.sh       # Build CLI tool
```

## Scripts

### `generate-proto.sh`
Generates Protocol Buffer code from `sdk/proto/plato.proto`.

**Output:**
- `sdk/models/plato.pb.go` - Generated Go models

**Requirements:**
- `protoc` (Protocol Buffer compiler)
- `protoc-gen-go` (Go protobuf plugin)

### `build-sdk.sh`
Builds the core Go SDK.

**Steps:**
1. Runs `go mod tidy` to update dependencies
2. Builds all packages with `go build ./...`
3. Runs tests with `go test ./...`

**Output:** Compiled SDK packages

### `build-bindings.sh`
Builds the C shared library for language bindings.

**Steps:**
1. Updates dependencies in `sdk/bindings/c/`
2. Builds shared library with `go build -buildmode=c-shared`

**Output:**
- `sdk/bindings/c/libplato.dylib` (macOS)
- `sdk/bindings/c/libplato.so` (Linux)

### `build-cli.sh`
Builds the Plato CLI tool with version information.

**Steps:**
1. Updates dependencies in `cli/`
2. Builds binary with version/commit/timestamp ldflags
3. Creates `cli/plato` binary

**Output:** `cli/plato` executable

### `build-all.sh`
Runs all build scripts in sequence for a complete build.

**Order:**
1. Generate protobuf code
2. Build SDK
3. Build C bindings
4. Build CLI

## Development Workflow

### Making Model Changes

```bash
# 1. Edit the proto file
vim sdk/proto/plato.proto

# 2. Regenerate code
./scripts/generate-proto.sh

# 3. Build and test
./scripts/build-all.sh
```

### Working on SDK

```bash
# Make changes to SDK code
vim sdk/services/sandbox.go

# Build and test
./scripts/build-sdk.sh
```

### Working on CLI

```bash
# Make changes to CLI code
vim cli/main.go

# Build CLI
./scripts/build-cli.sh

# Test it
./cli/plato
```

### Full Clean Build

```bash
# Clean and rebuild everything
rm -rf sdk/models/plato.pb.go
rm -rf sdk/bindings/c/libplato.*
rm -rf cli/plato
./scripts/build-all.sh
```

## Project Structure

```
plato-client/
├── scripts/               # Build scripts (this directory)
│   ├── generate-proto.sh
│   ├── build-sdk.sh
│   ├── build-bindings.sh
│   ├── build-cli.sh
│   ├── build-all.sh
│   └── README.md
├── sdk/                   # Core Go SDK
│   ├── proto/            # Protobuf definitions
│   ├── models/           # Generated models
│   ├── services/         # Service implementations
│   └── bindings/         # Language bindings
│       └── c/           # C shared library
└── cli/                  # CLI tool
    └── plato            # Built binary
```

## Make Everything Executable

```bash
chmod +x scripts/*.sh
```

## Troubleshooting

### "protoc not found"
```bash
brew install protobuf
```

### "protoc-gen-go not found"
```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
```

### "missing go.sum entry"
```bash
# Run in the affected directory
go mod tidy
```

### Build fails after proto changes
```bash
# Clean and rebuild
./scripts/generate-proto.sh
./scripts/build-all.sh
```
