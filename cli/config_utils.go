package main

import (
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

	var config models.PlatoConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, err
	}

	return &config, nil
}

// GetPlatoConfigDir returns the absolute directory path where plato-config.yml is located
func GetPlatoConfigDir() (string, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}

	// Check if plato-config.yml exists in current directory
	configPath := filepath.Join(cwd, platoConfigFilename)
	if _, err := os.Stat(configPath); err != nil {
		return "", err
	}

	return cwd, nil
}

// SavePlatoConfig saves a PlatoConfig to plato-config.yml in the current directory
func SavePlatoConfig(config *models.PlatoConfig) error {
	data, err := yaml.Marshal(config)
	if err != nil {
		return err
	}

	return os.WriteFile(platoConfigFilename, data, 0644)
}

// GetCurrentDir returns the current working directory
func GetCurrentDir() string {
	dir, err := os.Getwd()
	if err != nil {
		return "."
	}
	return filepath.Base(dir)
}
