// Package utils provides network utilities for the Plato CLI.
//
// This file handles port management and network-related operations.
package utils

import (
	"fmt"
	"net"
	"strings"
)

// FindFreePort finds an available port on the local machine
func FindFreePort() (int, error) {
	addr, err := net.ResolveTCPAddr("tcp", "localhost:0")
	if err != nil {
		return 0, err
	}

	l, err := net.ListenTCP("tcp", addr)
	if err != nil {
		return 0, err
	}
	defer l.Close()
	return l.Addr().(*net.TCPAddr).Port, nil
}

// FindFreePortPreferred tries to use the preferred port, falls back to any free port
func FindFreePortPreferred(preferred int) (int, error) {
	// Try preferred port first
	addr := fmt.Sprintf("localhost:%d", preferred)
	l, err := net.Listen("tcp", addr)
	if err == nil {
		// Port is available
		port := l.Addr().(*net.TCPAddr).Port
		l.Close()
		return port, nil
	}

	// Preferred port not available, find any free port
	return FindFreePort()
}

// IsPortAvailable checks if a port is available for use
func IsPortAvailable(port int) bool {
	addr := fmt.Sprintf("localhost:%d", port)
	l, err := net.Listen("tcp", addr)
	if err != nil {
		return false
	}
	l.Close()
	return true
}

// ProxyConfig holds the proxy server configuration
type ProxyConfig struct {
	Server string // e.g., "proxy.plato.so:9000" or "proxy.localhost:9000"
	Secure bool   // Whether to use the -E (secure) flag
}

// GetProxyConfig returns the appropriate proxy configuration based on the base URL.
// If the base URL contains "localhost", it returns proxy.localhost:9000 without secure flag.
// Otherwise, it returns proxy.plato.so:9000 with secure flag.
func GetProxyConfig(baseURL string) ProxyConfig {
	if strings.Contains(baseURL, "localhost") {
		return ProxyConfig{
			Server: "proxy.localhost:9000",
			Secure: false,
		}
	}
	return ProxyConfig{
		Server: "proxy.plato.so:9000",
		Secure: true,
	}
}
