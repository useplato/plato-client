// Package utils provides SSH configuration utilities for the Plato CLI.
//
// This file handles reading, parsing, and updating the user's ~/.ssh/config file
// to add or manage SSH host entries for Plato VM sandboxes.
package utils

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

// ReadSSHPublicKey reads the user's SSH public key from ~/.ssh directory
// It tries common key files in order: id_ed25519.pub, id_rsa.pub
// Returns both the public key content and the path to the private key file
func ReadSSHPublicKey() (string, error) {
	sshDir := filepath.Join(os.Getenv("HOME"), ".ssh")

	// Try common SSH public key file names in order of preference
	keyFiles := []string{"id_ed25519.pub", "id_rsa.pub", "id_ecdsa.pub"}

	for _, keyFile := range keyFiles {
		keyPath := filepath.Join(sshDir, keyFile)
		data, err := os.ReadFile(keyPath)
		if err == nil {
			// Found a key, return its content (trimmed of whitespace)
			return strings.TrimSpace(string(data)), nil
		}
		// If file doesn't exist, try next key file
		if !os.IsNotExist(err) {
			// If error is not "file doesn't exist", return the error
			return "", fmt.Errorf("error reading %s: %w", keyPath, err)
		}
	}

	// No SSH public key found
	return "", fmt.Errorf("no SSH public key found in %s (tried: %s)", sshDir, strings.Join(keyFiles, ", "))
}

// GetSSHPrivateKeyPath returns the path to the SSH private key
// It tries common key files in order and returns the path of the first one found
func GetSSHPrivateKeyPath() (string, error) {
	sshDir := filepath.Join(os.Getenv("HOME"), ".ssh")

	// Try common SSH public key file names in order of preference
	// We check for the public key and return the private key path
	keyFiles := []string{"id_ed25519.pub", "id_rsa.pub", "id_ecdsa.pub"}

	for _, keyFile := range keyFiles {
		publicKeyPath := filepath.Join(sshDir, keyFile)
		if _, err := os.Stat(publicKeyPath); err == nil {
			// Found the public key, return the private key path (remove .pub extension)
			privateKeyPath := strings.TrimSuffix(publicKeyPath, ".pub")
			return privateKeyPath, nil
		}
	}

	// No SSH key found
	return "", fmt.Errorf("no SSH private key found in %s", sshDir)
}

// ReadSSHConfig reads SSH config file, returns empty string if doesn't exist
func ReadSSHConfig() (string, error) {
	sshConfigPath := filepath.Join(os.Getenv("HOME"), ".ssh", "config")
	data, err := os.ReadFile(sshConfigPath)
	if err != nil {
		if os.IsNotExist(err) {
			return "", nil
		}
		return "", err
	}
	return string(data), nil
}

// HostExistsInConfig checks if a hostname exists in SSH config
func HostExistsInConfig(hostname, configContent string) bool {
	return strings.Contains(configContent, fmt.Sprintf("Host %s", hostname))
}

// FindAvailableHostname finds next available hostname by appending numbers if needed
func FindAvailableHostname(baseHostname, configContent string) string {
	hostname := baseHostname
	counter := 1

	for HostExistsInConfig(hostname, configContent) {
		hostname = fmt.Sprintf("%s-%d", baseHostname, counter)
		counter++
	}

	return hostname
}

// RemoveSSHHostFromConfig removes a host entry from SSH config content
func RemoveSSHHostFromConfig(hostname, configContent string) string {
	lines := strings.Split(configContent, "\n")
	var newLines []string
	skipBlock := false

	for _, line := range lines {
		if strings.TrimSpace(line) == fmt.Sprintf("Host %s", hostname) {
			skipBlock = true
			continue
		} else if strings.HasPrefix(line, "Host ") && skipBlock {
			skipBlock = false
			newLines = append(newLines, line)
		} else if !skipBlock {
			newLines = append(newLines, line)
		}
	}

	return strings.TrimRight(strings.Join(newLines, "\n"), "\n")
}

// WriteSSHConfig writes SSH config content to file
func WriteSSHConfig(configContent string) error {
	sshConfigDir := filepath.Join(os.Getenv("HOME"), ".ssh")
	if err := os.MkdirAll(sshConfigDir, 0700); err != nil {
		return err
	}

	sshConfigPath := filepath.Join(sshConfigDir, "config")
	content := configContent
	if content != "" && !strings.HasSuffix(content, "\n") {
		content += "\n"
	}

	return os.WriteFile(sshConfigPath, []byte(content), 0600)
}

// CreateTempSSHConfig creates a temporary SSH config file for a specific host
// Returns the path to the temporary config file
func CreateTempSSHConfig(hostname string, port int, jobGroupID string, username string) (string, error) {
	// Find proxytunnel path
	proxytunnelPath, err := exec.LookPath("proxytunnel")
	if err != nil {
		return "", fmt.Errorf("proxytunnel not found in PATH: %w", err)
	}

	// Get the private key path to include in the SSH config
	privateKeyPath, err := GetSSHPrivateKeyPath()
	if err != nil {
		return "", fmt.Errorf("failed to find SSH private key: %w", err)
	}

	// Create temp config content
	configContent := fmt.Sprintf(`Host %s
    HostName localhost
    Port %d
    User %s
    IdentityFile %s
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ConnectTimeout 10
    ProxyCommand %s -E -p proxy.plato.so:9000 -P '%s@22:newpass' -d %%h:%%p --no-check-certificate
    ServerAliveInterval 30
    ServerAliveCountMax 3
    TCPKeepAlive yes
`, hostname, port, username, privateKeyPath, proxytunnelPath, jobGroupID)

	// Create temp file in ~/.plato directory
	platoDir := filepath.Join(os.Getenv("HOME"), ".plato")
	if err := os.MkdirAll(platoDir, 0700); err != nil {
		return "", fmt.Errorf("failed to create .plato directory: %w", err)
	}

	// Extract number from hostname (e.g., "sandbox-1" -> "1")
	// Use simple naming: ssh_N.conf
	numStr := strings.TrimPrefix(hostname, "sandbox-")
	tempConfigPath := filepath.Join(platoDir, fmt.Sprintf("ssh_%s.conf", numStr))
	if err := os.WriteFile(tempConfigPath, []byte(configContent), 0600); err != nil {
		return "", fmt.Errorf("failed to write temp SSH config: %w", err)
	}

	return tempConfigPath, nil
}

// AppendSSHHostEntry appends a new SSH host entry to config
func AppendSSHHostEntry(hostname string, port int, jobGroupID string, username string) error {
	configContent, err := ReadSSHConfig()
	if err != nil {
		return err
	}

	// Find proxytunnel path
	proxytunnelPath, err := exec.LookPath("proxytunnel")
	if err != nil {
		return fmt.Errorf("proxytunnel not found in PATH: %w", err)
	}

	// Get the private key path to include in the SSH config
	privateKeyPath, err := GetSSHPrivateKeyPath()
	if err != nil {
		return fmt.Errorf("failed to find SSH private key: %w", err)
	}

	configWithProxy := fmt.Sprintf(`Host %s
    HostName localhost
    Port %d
    User %s
    IdentityFile %s
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ConnectTimeout 10
    ProxyCommand %s -E -p proxy.plato.so:9000 -P '%s@22:newpass' -d %%h:%%p --no-check-certificate
    ServerAliveInterval 30
    ServerAliveCountMax 3
    TCPKeepAlive yes
    `, hostname, port, username, privateKeyPath, proxytunnelPath, jobGroupID)

	if configContent != "" {
		configContent = strings.TrimRight(configContent, "\n") + "\n\n" + configWithProxy
	} else {
		configContent = configWithProxy
	}

	return WriteSSHConfig(configContent)
}

// getNextSandboxNumber finds the next available sandbox number by checking existing config files
func getNextSandboxNumber() int {
	platoDir := filepath.Join(os.Getenv("HOME"), ".plato")
	files, err := os.ReadDir(platoDir)
	if err != nil {
		return 1 // If directory doesn't exist or error, start at 1
	}

	maxNum := 0
	for _, file := range files {
		if strings.HasPrefix(file.Name(), "ssh_") && strings.HasSuffix(file.Name(), ".conf") {
			// Extract number from ssh_N.conf
			name := strings.TrimPrefix(file.Name(), "ssh_")
			name = strings.TrimSuffix(name, ".conf")
			if num, err := strconv.Atoi(name); err == nil && num > maxNum {
				maxNum = num
			}
		}
	}
	return maxNum + 1
}

// SetupSSHConfig creates a temporary SSH config file and returns the hostname and config path
// Returns (hostname, configPath, error)
func SetupSSHConfig(localPort int, jobPublicID string, username string) (string, string, error) {
	// Get next available sandbox number for a simple hostname
	sandboxNum := getNextSandboxNumber()
	sshHost := fmt.Sprintf("sandbox-%d", sandboxNum)

	// Create temporary SSH config file with simple name
	configPath, err := CreateTempSSHConfig(sshHost, localPort, jobPublicID, username)
	if err != nil {
		return "", "", fmt.Errorf("failed to create temp SSH config: %w", err)
	}

	return sshHost, configPath, nil
}

// CleanupSSHConfig removes a SSH host entry from config
func CleanupSSHConfig(hostname string) error {
	existingConfig, err := ReadSSHConfig()
	if err != nil {
		return err
	}

	if existingConfig == "" {
		return nil
	}

	updatedConfig := RemoveSSHHostFromConfig(hostname, existingConfig)
	return WriteSSHConfig(updatedConfig)
}

// UpdateSSHConfigPassword updates an existing SSH host entry to enable password authentication
func UpdateSSHConfigPassword(hostname, password string) error {
	LogDebug("UpdateSSHConfigPassword called for hostname=%s, password=%s", hostname, password)

	existingConfig, err := ReadSSHConfig()
	if err != nil {
		return err
	}

	if existingConfig == "" {
		return fmt.Errorf("SSH config is empty")
	}

	if !HostExistsInConfig(hostname, existingConfig) {
		return fmt.Errorf("host %s not found in SSH config", hostname)
	}

	LogDebug("Found host in SSH config, updating...")

	lines := strings.Split(existingConfig, "\n")
	var newLines []string
	inTargetHost := false

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Check if we're entering the target host block
		if trimmed == fmt.Sprintf("Host %s", hostname) {
			inTargetHost = true
			newLines = append(newLines, line)
			// Add password comment right after Host line
			newLines = append(newLines, fmt.Sprintf("    # Password: %s", password))
			continue
		}

		// Check if we're entering a different host block
		if strings.HasPrefix(trimmed, "Host ") && trimmed != fmt.Sprintf("Host %s", hostname) {
			inTargetHost = false
		}

		// If we're in the target host and it's the IdentitiesOnly line, change it
		if inTargetHost && strings.HasPrefix(trimmed, "IdentitiesOnly") {
			newLines = append(newLines, "    IdentitiesOnly no")
			continue
		}

		// Skip lines that we'll replace or that are already password comments
		if inTargetHost && strings.HasPrefix(trimmed, "# Password:") {
			continue
		}

		newLines = append(newLines, line)
	}

	updatedConfig := strings.Join(newLines, "\n")
	return WriteSSHConfig(updatedConfig)
}

// UpdateSSHConfigUser updates the username for an existing SSH host entry
func UpdateSSHConfigUser(hostname, username string) error {
	existingConfig, err := ReadSSHConfig()
	if err != nil {
		return err
	}

	if existingConfig == "" {
		return fmt.Errorf("SSH config is empty")
	}

	if !HostExistsInConfig(hostname, existingConfig) {
		return fmt.Errorf("host %s not found in SSH config", hostname)
	}

	lines := strings.Split(existingConfig, "\n")
	var newLines []string
	inTargetHost := false

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Check if we're entering the target host block
		if trimmed == fmt.Sprintf("Host %s", hostname) {
			inTargetHost = true
			newLines = append(newLines, line)
			continue
		}

		// Check if we're entering a different host block
		if strings.HasPrefix(trimmed, "Host ") && trimmed != fmt.Sprintf("Host %s", hostname) {
			inTargetHost = false
		}

		// If we're in the target host and it's the User line, update it
		if inTargetHost && strings.HasPrefix(trimmed, "User ") {
			newLines = append(newLines, fmt.Sprintf("    User %s", username))
			continue
		}

		newLines = append(newLines, line)
	}

	updatedConfig := strings.Join(newLines, "\n")
	return WriteSSHConfig(updatedConfig)
}

// UpdateSSHConfigFileUser updates the username for a host in a specific SSH config file
func UpdateSSHConfigFileUser(configPath, hostname, username string) error {
	configContent, err := os.ReadFile(configPath)
	if err != nil {
		return fmt.Errorf("failed to read SSH config: %w", err)
	}

	existingConfig := string(configContent)
	if existingConfig == "" {
		return fmt.Errorf("SSH config is empty")
	}

	if !HostExistsInConfig(hostname, existingConfig) {
		return fmt.Errorf("host %s not found in SSH config", hostname)
	}

	lines := strings.Split(existingConfig, "\n")
	var newLines []string
	inTargetHost := false

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Check if we're entering the target host block
		if trimmed == fmt.Sprintf("Host %s", hostname) {
			inTargetHost = true
			newLines = append(newLines, line)
			continue
		}

		// Check if we're entering a different host block
		if strings.HasPrefix(trimmed, "Host ") && trimmed != fmt.Sprintf("Host %s", hostname) {
			inTargetHost = false
		}

		// If we're in the target host and it's the User line, update it
		if inTargetHost && strings.HasPrefix(trimmed, "User ") {
			newLines = append(newLines, fmt.Sprintf("    User %s", username))
			continue
		}

		newLines = append(newLines, line)
	}

	updatedConfig := strings.Join(newLines, "\n")
	return os.WriteFile(configPath, []byte(updatedConfig), 0600)
}

// UpdateSSHConfigFilePassword updates password for a host in a specific SSH config file
func UpdateSSHConfigFilePassword(configPath, hostname, password string) error {
	LogDebug("UpdateSSHConfigFilePassword called for configPath=%s, hostname=%s, password=%s", configPath, hostname, password)

	configContent, err := os.ReadFile(configPath)
	if err != nil {
		return fmt.Errorf("failed to read SSH config: %w", err)
	}

	existingConfig := string(configContent)
	if existingConfig == "" {
		return fmt.Errorf("SSH config is empty")
	}

	if !HostExistsInConfig(hostname, existingConfig) {
		return fmt.Errorf("host %s not found in SSH config", hostname)
	}

	LogDebug("Found host in SSH config, updating...")

	lines := strings.Split(existingConfig, "\n")
	var newLines []string
	inTargetHost := false

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Check if we're entering the target host block
		if trimmed == fmt.Sprintf("Host %s", hostname) {
			inTargetHost = true
			newLines = append(newLines, line)
			// Add password comment right after Host line
			newLines = append(newLines, fmt.Sprintf("    # Password: %s", password))
			continue
		}

		// Check if we're entering a different host block
		if strings.HasPrefix(trimmed, "Host ") && trimmed != fmt.Sprintf("Host %s", hostname) {
			inTargetHost = false
		}

		// Skip existing password comments
		if inTargetHost && strings.HasPrefix(trimmed, "# Password:") {
			continue
		}

		newLines = append(newLines, line)
	}

	updatedConfig := strings.Join(newLines, "\n")
	LogDebug("Updated SSH config, writing to file...")
	return os.WriteFile(configPath, []byte(updatedConfig), 0600)
}
