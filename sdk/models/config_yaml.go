package models

import (
	"encoding/json"
	"fmt"

	"gopkg.in/yaml.v3"
)

// UnmarshalYAML implements custom YAML unmarshaling for PlatoConfig
// This handles the conversion of listener maps to JSON strings
func (c *PlatoConfig) UnmarshalYAML(value *yaml.Node) error {
	// Create a temporary structure that matches the YAML structure
	var temp struct {
		Service  *string `yaml:"service"`
		Datasets map[string]struct {
			Compute  *SimConfigCompute             `yaml:"compute"`
			Metadata *SimConfigMetadata            `yaml:"metadata"`
			Services map[string]*SimConfigService  `yaml:"services"`
			Listeners map[string]map[string]interface{} `yaml:"listeners"` // Raw maps
		} `yaml:"datasets"`
	}

	if err := value.Decode(&temp); err != nil {
		return err
	}

	// Convert to PlatoConfig
	c.Service = temp.Service
	c.Datasets = make(map[string]*SimConfigDataset)

	for name, dataset := range temp.Datasets {
		config := &SimConfigDataset{
			Compute:  dataset.Compute,
			Metadata: dataset.Metadata,
			Services: dataset.Services,
			Listeners: make(map[string]string),
		}

		// Convert listener maps to JSON strings
		for listenerName, listenerData := range dataset.Listeners {
			jsonBytes, err := json.Marshal(listenerData)
			if err != nil {
				return fmt.Errorf("failed to marshal listener %s: %w", listenerName, err)
			}
			config.Listeners[listenerName] = string(jsonBytes)
		}

		c.Datasets[name] = config
	}

	return nil
}
