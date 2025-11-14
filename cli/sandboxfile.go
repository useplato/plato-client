// Package main provides sandbox file management utilities for the Plato CLI.
//
// This file implements functions to write and remove a .sandbox.yaml file
// in the current working directory when a VM is started or stopped.
package main

import (
	"fmt"
	"os"
	"plato-sdk/models"

	"gopkg.in/yaml.v3"
)

// SandboxFileData represents the contents of .sandbox.yaml
type SandboxFileData struct {
	PublicID          string  `yaml:"public_id"`
	JobGroupID        string  `yaml:"job_group_id"`
	URL               string  `yaml:"url"`
	Dataset           string  `yaml:"dataset"`
	PlatoConfigPath   string  `yaml:"plato_config_path"`
	ArtifactID        *string `yaml:"artifact_id,omitempty"`
	Version           *string `yaml:"version,omitempty"`
	SSHHost           string  `yaml:"ssh_host"`
	SSHConfigPath     string  `yaml:"ssh_config_path"`
	SSHPrivateKeyPath string  `yaml:"ssh_private_key_path"`
}

// WriteSandboxFile writes .sandbox.yaml to the current working directory
func WriteSandboxFile(sandbox *models.Sandbox, dataset string, platoConfigPath string, artifactID *string, version *string, sshHost string, sshConfigPath string, sshPrivateKeyPath string) error {
	data := SandboxFileData{
		PublicID:          sandbox.PublicId,
		JobGroupID:        sandbox.JobGroupId,
		URL:               sandbox.Url,
		Dataset:           dataset,
		PlatoConfigPath:   platoConfigPath,
		ArtifactID:        artifactID,
		Version:           version,
		SSHHost:           sshHost,
		SSHConfigPath:     sshConfigPath,
		SSHPrivateKeyPath: sshPrivateKeyPath,
	}

	yamlData, err := yaml.Marshal(&data)
	if err != nil {
		return fmt.Errorf("failed to marshal sandbox data: %w", err)
	}

	if err := os.WriteFile(".sandbox.yaml", yamlData, 0644); err != nil {
		return fmt.Errorf("failed to write .sandbox.yaml: %w", err)
	}

	return nil
}

// RemoveSandboxFile removes .sandbox.yaml from the current working directory
func RemoveSandboxFile() error {
	err := os.Remove(".sandbox.yaml")
	if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("failed to remove .sandbox.yaml: %w", err)
	}
	return nil
}

// ReadSandboxFile reads .sandbox.yaml from the current working directory
func ReadSandboxFile() (*SandboxFileData, error) {
	data, err := os.ReadFile(".sandbox.yaml")
	if err != nil {
		return nil, fmt.Errorf("failed to read .sandbox.yaml: %w", err)
	}

	var sandboxData SandboxFileData
	if err := yaml.Unmarshal(data, &sandboxData); err != nil {
		return nil, fmt.Errorf("failed to unmarshal .sandbox.yaml: %w", err)
	}

	return &sandboxData, nil
}
