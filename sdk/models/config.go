// Package models provides data structures for simulator configuration.
//
// This file defines the complete plato-config.yml structure, including compute
// resources, metadata, services (docker/docker-compose), listeners, and datasets.
// These models are used when configuring simulators and creating sandboxes with
// specific resource requirements and service definitions.
package models

// SimConfigCompute represents compute resource configuration for a simulator
type SimConfigCompute struct {
	CPUs               int `json:"cpus" yaml:"cpus"`
	Memory             int `json:"memory" yaml:"memory"`
	Disk               int `json:"disk" yaml:"disk"`
	AppPort            int `json:"app_port" yaml:"app_port"`
	PlatoMessagingPort int `json:"plato_messaging_port" yaml:"plato_messaging_port"`
}

// SimConfigMetadata represents metadata configuration for a simulator
type SimConfigMetadata struct {
	Favicon       string              `json:"favicon" yaml:"favicon"`
	Name          string              `json:"name" yaml:"name"`
	Description   string              `json:"description" yaml:"description"`
	SourceCodeURL string              `json:"source_code_url" yaml:"source_code_url"`
	StartURL      string              `json:"start_url" yaml:"start_url"`
	License       string              `json:"license" yaml:"license"`
	Variables     []map[string]string `json:"variables" yaml:"variables"`
	FlowsPath     *string             `json:"flows_path,omitempty" yaml:"flows_path,omitempty"`
}

// SimConfigService represents service configuration (docker-compose or docker)
type SimConfigService struct {
	Type                      string   `json:"type" yaml:"type"`
	File                      string   `json:"file,omitempty" yaml:"file,omitempty"`
	RequiredHealthyContainers []string `json:"required_healthy_containers,omitempty" yaml:"required_healthy_containers,omitempty"`
	HealthyWaitTimeout        int      `json:"healthy_wait_timeout,omitempty" yaml:"healthy_wait_timeout,omitempty"`
}

// SimConfigListener represents a mutation listener configuration (interface for different types)
type SimConfigListener map[string]interface{}

// SimConfigDataset represents configuration for a simulator dataset
type SimConfigDataset struct {
	Compute   SimConfigCompute              `json:"compute" yaml:"compute"`
	Metadata  SimConfigMetadata             `json:"metadata" yaml:"metadata"`
	Services  map[string]*SimConfigService  `json:"services" yaml:"services"`
	Listeners map[string]*SimConfigListener `json:"listeners" yaml:"listeners"`
}

// PlatoConfig represents the complete plato-config.yml structure
type PlatoConfig struct {
	Service  string                      `json:"service,omitempty" yaml:"service,omitempty"`
	Datasets map[string]SimConfigDataset `json:"datasets" yaml:"datasets"`
}

// DefaultPlatoConfig creates a default Plato configuration
func DefaultPlatoConfig(dataset string) *PlatoConfig {
	return &PlatoConfig{
		Datasets: map[string]SimConfigDataset{
			dataset: {
				Compute: SimConfigCompute{
					CPUs:               1,
					Memory:             512,
					Disk:               10240,
					AppPort:            8080,
					PlatoMessagingPort: 7000,
				},
				Metadata: SimConfigMetadata{
					Favicon:       "https://plato.so/favicon.ico",
					Name:          "Plato Simulator",
					Description:   "A Plato simulator environment",
					SourceCodeURL: "https://github.com/useplato/plato",
					StartURL:      "http://localhost:8080",
					License:       "MIT",
					Variables: []map[string]string{
						{"name": "PLATO_API_KEY", "value": "your-api-key"},
					},
				},
				Services: map[string]*SimConfigService{
					"main_app": {
						Type:                      "docker-compose",
						File:                      "docker-compose.yml",
						RequiredHealthyContainers: []string{"all"},
						HealthyWaitTimeout:        300,
					},
				},
				Listeners: map[string]*SimConfigListener{},
			},
		},
	}
}
