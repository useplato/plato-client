package utils

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

// FindProxytunnelPath finds the proxytunnel binary, preferring bundled binary over system installation
func FindProxytunnelPath() (string, error) {
	// First, try to find bundled binary relative to the executable
	execPath, err := os.Executable()
	if err == nil {
		// Get directory containing the executable
		execDir := filepath.Dir(execPath)

		// Determine platform-specific binary name
		var binaryName string
		switch runtime.GOOS {
		case "darwin":
			if runtime.GOARCH == "arm64" {
				binaryName = "proxytunnel-darwin-arm64"
			} else {
				binaryName = "proxytunnel-darwin-amd64"
			}
		case "linux":
			if runtime.GOARCH == "arm64" || runtime.GOARCH == "aarch64" {
				binaryName = "proxytunnel-linux-arm64"
			} else {
				binaryName = "proxytunnel-linux-amd64"
			}
		case "windows":
			binaryName = "proxytunnel.exe"
		default:
			binaryName = ""
		}

		if binaryName != "" {
			// Check in same directory as executable (for bundled binaries)
			bundledPath := filepath.Join(execDir, binaryName)
			if info, err := os.Stat(bundledPath); err == nil && !info.IsDir() {
				if isExecutable(bundledPath) {
					return bundledPath, nil
				}
			}

			// Also check in ../bin relative to executable (for development)
			bundledPath = filepath.Join(execDir, "..", "bin", binaryName)
			if info, err := os.Stat(bundledPath); err == nil && !info.IsDir() {
				if isExecutable(bundledPath) {
					return bundledPath, nil
				}
			}

			// Check in ./bin relative to executable (alternative structure)
			bundledPath = filepath.Join(execDir, "bin", binaryName)
			if info, err := os.Stat(bundledPath); err == nil && !info.IsDir() {
				if isExecutable(bundledPath) {
					return bundledPath, nil
				}
			}
		}
	}

	// Fall back to system PATH
	path, err := exec.LookPath("proxytunnel")
	if err == nil {
		return path, nil
	}

	// Check common installation locations
	commonPaths := []string{
		"/opt/homebrew/bin/proxytunnel",
		"/usr/local/bin/proxytunnel",
		"/usr/bin/proxytunnel",
		"/bin/proxytunnel",
	}

	for _, candidate := range commonPaths {
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
			if isExecutable(candidate) {
				return candidate, nil
			}
		}
	}

	return "", fmt.Errorf("proxytunnel not found (checked bundled binary, PATH, and common locations)")
}

// isExecutable checks if a file is executable
func isExecutable(path string) bool {
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	if info.IsDir() {
		return false
	}
	// Check if file has execute permission (Unix-like systems)
	if runtime.GOOS != "windows" {
		if info.Mode()&0111 == 0 {
			return false
		}
	}
	return true
}
