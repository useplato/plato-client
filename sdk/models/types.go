// Package models provides clean data structures for Plato platform
// Generated from OpenAPI schema: sdk/openapi/plato.yaml
package models

// SimConfigCompute defines compute resource configuration
type SimConfigCompute struct {
	Cpus               int32 `json:"cpus" yaml:"cpus"`
	Memory             int32 `json:"memory" yaml:"memory"`
	Disk               int32 `json:"disk" yaml:"disk"`
	AppPort            int32 `json:"app_port" yaml:"app_port"`
	PlatoMessagingPort int32 `json:"plato_messaging_port" yaml:"plato_messaging_port"`
}

// Variable defines an environment variable
type Variable struct {
	Name  string `json:"name" yaml:"name"`
	Value string `json:"value" yaml:"value"`
}

// SimConfigMetadata defines metadata for a simulator
type SimConfigMetadata struct {
	Favicon       string     `json:"favicon,omitempty" yaml:"favicon,omitempty"`
	Name          string     `json:"name" yaml:"name"`
	Description   string     `json:"description,omitempty" yaml:"description,omitempty"`
	SourceCodeUrl string     `json:"source_code_url,omitempty" yaml:"source_code_url,omitempty"`
	StartUrl      string     `json:"start_url,omitempty" yaml:"start_url,omitempty"`
	License       string     `json:"license,omitempty" yaml:"license,omitempty"`
	Variables     []Variable `json:"variables,omitempty" yaml:"variables,omitempty"`
	FlowsPath     string     `json:"flows_path,omitempty" yaml:"flows_path,omitempty"`
}

// SimConfigService defines a service configuration
type SimConfigService struct {
	Type                       string   `json:"type" yaml:"type"`
	File                       string   `json:"file,omitempty" yaml:"file,omitempty"`
	RequiredHealthyContainers  []string `json:"required_healthy_containers,omitempty" yaml:"required_healthy_containers,omitempty"`
	HealthyWaitTimeout         int32    `json:"healthy_wait_timeout,omitempty" yaml:"healthy_wait_timeout,omitempty"`
}

// SimConfigListener defines a listener configuration (DB, File, or Proxy)
type SimConfigListener struct {
	Type string `json:"type" yaml:"type"`

	// DB listener fields
	DbType     string `json:"db_type,omitempty" yaml:"db_type,omitempty"`
	DbHost     string `json:"db_host,omitempty" yaml:"db_host,omitempty"`
	DbPort     int32  `json:"db_port,omitempty" yaml:"db_port,omitempty"`
	DbUser     string `json:"db_user,omitempty" yaml:"db_user,omitempty"`
	DbPassword string `json:"db_password,omitempty" yaml:"db_password,omitempty"`
	DbDatabase string `json:"db_database,omitempty" yaml:"db_database,omitempty"`

	// File listener fields
	TargetDir      string   `json:"target_dir,omitempty" yaml:"target_dir,omitempty"`
	WatchEnabled   bool     `json:"watch_enabled,omitempty" yaml:"watch_enabled,omitempty"`
	WatchPatterns  []string `json:"watch_patterns,omitempty" yaml:"watch_patterns,omitempty"`
	IgnorePatterns []string `json:"ignore_patterns,omitempty" yaml:"ignore_patterns,omitempty"`
	SeedDataPath   string   `json:"seed_data_path,omitempty" yaml:"seed_data_path,omitempty"`

	// Common fields
	SeedDataPaths []string `json:"seed_data_paths,omitempty" yaml:"seed_data_paths,omitempty"`
	Volumes       []string `json:"volumes,omitempty" yaml:"volumes,omitempty"`
}

// SimConfigDataset defines a complete dataset configuration
type SimConfigDataset struct {
	Compute   SimConfigCompute              `json:"compute" yaml:"compute"`
	Metadata  SimConfigMetadata             `json:"metadata" yaml:"metadata"`
	Services  map[string]SimConfigService   `json:"services" yaml:"services,omitempty"`
	Listeners map[string]SimConfigListener  `json:"listeners" yaml:"listeners,omitempty"`
}

// PlatoConfig is the root plato-config.yml structure
type PlatoConfig struct {
	Service  string                       `json:"service,omitempty" yaml:"service,omitempty"`
	Datasets map[string]SimConfigDataset  `json:"datasets,omitempty" yaml:"datasets,omitempty"`
}

// Sandbox represents a VM sandbox
type Sandbox struct {
	JobId         string `json:"job_id" yaml:"job_id"`
	PublicId      string `json:"public_id" yaml:"public_id"`
	JobGroupId    string `json:"job_group_id" yaml:"job_group_id"`
	Url           string `json:"url,omitempty" yaml:"url,omitempty"`
	Status        string `json:"status,omitempty" yaml:"status,omitempty"`
	CorrelationId string `json:"correlation_id,omitempty" yaml:"correlation_id,omitempty"`
}

// Environment and SimulatorListItem are defined in environment.go and simulator.go

// CreateSnapshotRequest is a request to create a VM snapshot
type CreateSnapshotRequest struct {
	Service string `json:"service,omitempty"`
	GitHash string `json:"git_hash,omitempty"`
	Dataset string `json:"dataset,omitempty"`
}

// CreateSnapshotResponse is the response from creating a snapshot
type CreateSnapshotResponse struct {
	ArtifactId    string `json:"artifact_id"`
	Status        string `json:"status"`
	Timestamp     string `json:"timestamp"`
	CorrelationId string `json:"correlation_id"`
	S3Uri         string `json:"s3_uri"`
	GitHash       string `json:"git_hash,omitempty"`
}

// StartWorkerRequest is a request to start the Plato worker
type StartWorkerRequest struct {
	Service             string               `json:"service,omitempty"`
	Dataset             string               `json:"dataset"`
	PlatoDatasetConfig *SimConfigDataset   `json:"plato_dataset_config"`
	Timeout             *int32               `json:"timeout,omitempty"`
}

// StartWorkerResponse is the response from starting the worker
type StartWorkerResponse struct {
	Status        string `json:"status"`
	Timestamp     string `json:"timestamp"`
	CorrelationId string `json:"correlation_id"`
}

// SSHInfo contains SSH connection information for a sandbox
type SSHInfo struct {
	SSHCommand     string `json:"ssh_command"`
	SSHHost        string `json:"ssh_host"`
	SSHConfigPath  string `json:"ssh_config_path"`
	PublicID       string `json:"public_id"`
	PublicKey      string `json:"public_key"`
	PrivateKeyPath string `json:"private_key_path"`
}
