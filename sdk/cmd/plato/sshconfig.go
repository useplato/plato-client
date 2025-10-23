package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// readSSHConfig reads SSH config file, returns empty string if doesn't exist
func readSSHConfig() (string, error) {
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

// hostExistsInConfig checks if a hostname exists in SSH config
func hostExistsInConfig(hostname, configContent string) bool {
	return strings.Contains(configContent, fmt.Sprintf("Host %s", hostname))
}

// findAvailableHostname finds next available hostname by appending numbers if needed
func findAvailableHostname(baseHostname, configContent string) string {
	hostname := baseHostname
	counter := 1

	for hostExistsInConfig(hostname, configContent) {
		hostname = fmt.Sprintf("%s-%d", baseHostname, counter)
		counter++
	}

	return hostname
}

// removeSSHHostFromConfig removes a host entry from SSH config content
func removeSSHHostFromConfig(hostname, configContent string) string {
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

// writeSSHConfig writes SSH config content to file
func writeSSHConfig(configContent string) error {
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

// appendSSHHostEntry appends a new SSH host entry to config
func appendSSHHostEntry(hostname string, port int, jobGroupID string) error {
	configContent, err := readSSHConfig()
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
    User root
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ConnectTimeout 10
    ProxyCommand %s -E -p proxy.plato.so:9000 -P '%s@22:newpass' -d %%h:%%p --no-check-certificate
    ServerAliveInterval 30
    ServerAliveCountMax 3
    TCPKeepAlive yes
    `, hostname, port, proxytunnelPath, jobGroupID)

	if configContent != "" {
		configContent = strings.TrimRight(configContent, "\n") + "\n\n" + configWithProxy
	} else {
		configContent = configWithProxy
	}

	return writeSSHConfig(configContent)
}

// setupSSHConfig sets up SSH config with available hostname and returns the hostname
func setupSSHConfig(localPort int, jobGroupID string) (string, error) {
	sshConfigDir := filepath.Join(os.Getenv("HOME"), ".ssh")
	if err := os.MkdirAll(sshConfigDir, 0700); err != nil {
		return "", err
	}

	// Find next available sandbox hostname
	existingConfig, err := readSSHConfig()
	if err != nil {
		return "", err
	}

	sshHost := findAvailableHostname("sandbox", existingConfig)

	// Add SSH host entry
	if err := appendSSHHostEntry(sshHost, localPort, jobGroupID); err != nil {
		return "", fmt.Errorf("failed to append SSH host entry: %w", err)
	}

	return sshHost, nil
}

// cleanupSSHConfig removes a SSH host entry from config
func cleanupSSHConfig(hostname string) error {
	existingConfig, err := readSSHConfig()
	if err != nil {
		return err
	}

	if existingConfig == "" {
		return nil
	}

	updatedConfig := removeSSHHostFromConfig(hostname, existingConfig)
	return writeSSHConfig(updatedConfig)
}
