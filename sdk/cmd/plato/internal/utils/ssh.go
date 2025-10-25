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
	"strings"
)

// ReadSSHPublicKey reads the user's SSH public key from ~/.ssh directory
// It tries common key files in order: id_ed25519.pub, id_rsa.pub
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

	configWithProxy := fmt.Sprintf(`Host %s
    HostName localhost
    Port %d
    User %s
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ConnectTimeout 10
    ProxyCommand %s -E -p proxy.plato.so:9000 -P '%s@22:newpass' -d %%h:%%p --no-check-certificate
    ServerAliveInterval 30
    ServerAliveCountMax 3
    TCPKeepAlive yes
    `, hostname, port, username, proxytunnelPath, jobGroupID)

	if configContent != "" {
		configContent = strings.TrimRight(configContent, "\n") + "\n\n" + configWithProxy
	} else {
		configContent = configWithProxy
	}

	return WriteSSHConfig(configContent)
}

// SetupSSHConfig sets up SSH config with available hostname and returns the hostname
func SetupSSHConfig(localPort int, jobPublicID string, username string) (string, error) {
	sshConfigDir := filepath.Join(os.Getenv("HOME"), ".ssh")
	if err := os.MkdirAll(sshConfigDir, 0700); err != nil {
		return "", err
	}

	// Find next available sandbox hostname
	existingConfig, err := ReadSSHConfig()
	if err != nil {
		return "", err
	}

	sshHost := FindAvailableHostname("sandbox", existingConfig)

	// Add SSH host entry
	if err := AppendSSHHostEntry(sshHost, localPort, jobPublicID, username); err != nil {
		return "", fmt.Errorf("failed to append SSH host entry: %w", err)
	}

	return sshHost, nil
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
