# Plato Client

Complete client libraries and CLI for the Plato platform - manage sandbox VMs, simulators, and environments programmatically.

## Quick Start

```bash
# Build components
./scripts/generate-proto.sh  # Generate protobuf
./scripts/build-sdk.sh       # Build SDK
./scripts/build-cli.sh       # Build CLI

# Use the CLI
./cli/plato
```

## Project Structure

```
plato-client/
├── scripts/           # Build scripts
├── sdk/               # Go SDK (core)
├── cli/               # CLI tool
├── python/            # Legacy Python SDK
└── javascript/        # Legacy JavaScript SDK
```

## Components

- **Go SDK** (`sdk/`) - Core SDK with protobuf models
- **CLI Tool** (`cli/`) - Interactive terminal UI
- **C Bindings** (`sdk/bindings/c/`) - Shared library
- **Python SDK** (`sdk/bindings/python/`) - Python wrapper

## Building

```bash
# Full build
./scripts/build-all.sh

# Individual builds
./scripts/build-sdk.sh       # SDK only
./scripts/build-cli.sh       # CLI only
./scripts/build-bindings.sh  # C bindings only
```

## Documentation

- [Build Scripts](scripts/README.md) - Build system
- [SDK Guide](sdk/README.md) - SDK documentation
- [Protocol Buffers](sdk/proto/plato.proto) - Model definitions

## Requirements

- Go 1.21+
- Protocol Buffers compiler (`protoc`)

```bash
# macOS
brew install protobuf
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
```

## Development

```bash
# 1. Edit proto definitions
vim sdk/proto/plato.proto

# 2. Generate code
./scripts/generate-proto.sh

# 3. Build and test
./scripts/build-all.sh
```

See [scripts/README.md](scripts/README.md) and [sdk/README.md](sdk/README.md) for detailed guides.
