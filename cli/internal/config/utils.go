// Package config provides configuration utilities for the Plato CLI.
//
// This file handles loading and saving plato-config.yml files.
package config

import (
	"encoding/json"
	"os"
	"path/filepath"

	"plato-sdk/models"

	"gopkg.in/yaml.v3"
)

const platoConfigFilename = "plato-config.yml"

// ConfigExists checks if plato-config.yml exists in the current directory
func ConfigExists() bool {
	_, err := os.Stat(platoConfigFilename)
	return err == nil
}

// LoadPlatoConfig loads and parses plato-config.yml from the current directory
func LoadPlatoConfig() (*models.PlatoConfig, error) {
	data, err := os.ReadFile(platoConfigFilename)
	if err != nil {
		return nil, err
	}

	// First unmarshal YAML to a generic map
	var yamlData map[string]interface{}
	if err := yaml.Unmarshal(data, &yamlData); err != nil {
		return nil, err
	}

	// Then marshal to JSON and unmarshal to protobuf struct
	// This uses the protobuf JSON tags which match our YAML snake_case fields
	jsonData, err := json.Marshal(yamlData)
	if err != nil {
		return nil, err
	}

	var config models.PlatoConfig
	if err := json.Unmarshal(jsonData, &config); err != nil {
		return nil, err
	}

	return &config, nil
}

// SavePlatoConfig saves a PlatoConfig to plato-config.yml in the current directory
func SavePlatoConfig(config *models.PlatoConfig) error {
	data, err := yaml.Marshal(config)
	if err != nil {
		return err
	}

	return os.WriteFile(platoConfigFilename, data, 0644)
}

// GetCurrentDir returns the current working directory name
func GetCurrentDir() string {
	dir, err := os.Getwd()
	if err != nil {
		return "."
	}
	return filepath.Base(dir)
}
