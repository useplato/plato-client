# Makefile for building Plato C bindings shared library

.PHONY: all clean linux macos windows

# Default target
all: build

# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    TARGET = libplato.so
    BUILD_TARGET = linux
endif
ifeq ($(UNAME_S),Darwin)
    TARGET = libplato.dylib
    BUILD_TARGET = macos
endif
ifeq ($(OS),Windows_NT)
    TARGET = plato.dll
    BUILD_TARGET = windows
endif

# Build for current platform
build:
	@echo "Building for current platform ($(BUILD_TARGET))..."
	go build -buildmode=c-shared -o $(TARGET) sandbox.go
	@echo "Built: $(TARGET)"

# Build for Linux
linux:
	@echo "Building for Linux..."
	GOOS=linux GOARCH=amd64 go build -buildmode=c-shared -o libplato.so sandbox.go
	@echo "Built: libplato.so"

# Build for macOS
macos:
	@echo "Building for macOS (Intel)..."
	GOOS=darwin GOARCH=amd64 go build -buildmode=c-shared -o libplato_amd64.dylib sandbox.go
	@echo "Built: libplato_amd64.dylib"
	@echo "Building for macOS (Apple Silicon)..."
	GOOS=darwin GOARCH=arm64 go build -buildmode=c-shared -o libplato_arm64.dylib sandbox.go
	@echo "Built: libplato_arm64.dylib"
	@echo "Creating universal binary..."
	lipo -create libplato_amd64.dylib libplato_arm64.dylib -output libplato.dylib
	@echo "Built: libplato.dylib (universal)"

# Build for Windows
windows:
	@echo "Building for Windows..."
	GOOS=windows GOARCH=amd64 go build -buildmode=c-shared -o plato.dll sandbox.go
	@echo "Built: plato.dll"

# Build for all platforms
all-platforms: linux macos windows

# Clean build artifacts
clean:
	rm -f *.so *.dylib *.dll *.h *.a
	@echo "Cleaned build artifacts"

# Install to system library path (requires sudo on Linux/macOS)
install: build
ifeq ($(UNAME_S),Linux)
	sudo cp $(TARGET) /usr/local/lib/
	sudo ldconfig
endif
ifeq ($(UNAME_S),Darwin)
	sudo cp $(TARGET) /usr/local/lib/
endif
	@echo "Installed $(TARGET) to /usr/local/lib/"
