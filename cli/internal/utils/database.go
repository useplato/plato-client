// Package utils provides database utilities for the Plato CLI.
//
// This file handles database configuration, connection, and cleanup operations
// for pre-snapshot database maintenance tasks.
package utils

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	plato "plato-sdk"
	"plato-cli/internal/config"
	sdkutils "plato-sdk/utils"
)

// DBConfig represents database configuration for a simulator
type DBConfig struct {
	DBType    string   `json:"db_type"`
	User      string   `json:"user"`
	Password  string   `json:"password"`
	DestPort  int      `json:"dest_port"`
	Databases []string `json:"databases"`
}

// SimDBConfigs contains preset database configurations for known simulators
var SimDBConfigs = map[string]DBConfig{
	// PostgreSQL
	"bugsink":   {DBType: "postgresql", User: "bugsink", Password: "bugsink_password", DestPort: 5432, Databases: []string{"postgres", "bugsink"}},
	"calcom":    {DBType: "postgresql", User: "unicorn_user", Password: "magical_password", DestPort: 5432, Databases: []string{"postgres", "calendso"}},
	"discourse": {DBType: "postgresql", User: "discourse", Password: "discourse", DestPort: 5432, Databases: []string{"postgres", "discourse"}},
	// ... (include all others from original file)
}

// GetCustomDBConfigPath returns the path to the custom DB configs file
func GetCustomDBConfigPath() string {
	homeDir := os.Getenv("HOME")
	return filepath.Join(homeDir, ".plato", "custom_db_configs.json")
}

// LoadCustomDBConfigs loads user-defined DB configs from file
func LoadCustomDBConfigs() map[string]DBConfig {
	customConfigs := make(map[string]DBConfig)

	path := GetCustomDBConfigPath()
	data, err := os.ReadFile(path)
	if err != nil {
		return customConfigs
	}

	if err := json.Unmarshal(data, &customConfigs); err != nil {
		LogDebug("Failed to parse custom DB configs: %v", err)
		return customConfigs
	}

	LogDebug("Loaded %d custom DB configs", len(customConfigs))
	return customConfigs
}

// SaveCustomDBConfig saves a new custom DB config to file
func SaveCustomDBConfig(service string, config DBConfig) error {
	customConfigs := LoadCustomDBConfigs()
	customConfigs[service] = config

	configDir := filepath.Dir(GetCustomDBConfigPath())
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	data, err := json.MarshalIndent(customConfigs, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal configs: %w", err)
	}

	if err := os.WriteFile(GetCustomDBConfigPath(), data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	LogDebug("Saved custom DB config for service: %s", service)
	return nil
}

// GetDBConfigFromPlatoConfig extracts DB config from plato-config.yml for a specific dataset
func GetDBConfigFromPlatoConfig(dataset string) (DBConfig, bool) {
	platoConfig, err := config.LoadPlatoConfig()
	if err != nil {
		LogDebug("Failed to load plato-config.yml: %v", err)
		return DBConfig{}, false
	}

	datasetConfig, ok := platoConfig.Datasets[dataset]
	if !ok {
		LogDebug("Dataset '%s' not found in plato-config.yml", dataset)
		return DBConfig{}, false
	}

	// Look for a DB listener in the dataset's listeners
	for _, listener := range datasetConfig.Listeners {
		// Check if this is a DB listener
		if listener.Type != "db" {
			continue
		}

		// Extract DB configuration from the structured listener
		dbConfig := DBConfig{}

		dbConfig.DBType = listener.DbType
		dbConfig.User = listener.DbUser
		dbConfig.Password = listener.DbPassword
		dbConfig.DestPort = int(listener.DbPort)
		dbConfig.Databases = []string{listener.DbDatabase}

		LogDebug("Found DB config in plato-config.yml for dataset '%s': type=%s, port=%d", dataset, dbConfig.DBType, dbConfig.DestPort)
		return dbConfig, true
	}

	LogDebug("No DB listener found in plato-config.yml for dataset '%s'", dataset)
	return DBConfig{}, false
}

// GetDBConfig gets DB config for a service, checking in this order:
// 1. plato-config.yml for the current dataset
// 2. Custom configs from ~/.plato/custom_db_configs.json
// 3. Preset configs from SimDBConfigs
func GetDBConfig(service string) (DBConfig, bool) {
	// Try to get from plato-config.yml first (check for "base" dataset by default)
	if config, ok := GetDBConfigFromPlatoConfig("base"); ok {
		LogDebug("Using DB config from plato-config.yml for service: %s", service)
		return config, true
	}

	customConfigs := LoadCustomDBConfigs()
	if config, ok := customConfigs[service]; ok {
		LogDebug("Using custom DB config for service: %s", service)
		return config, true
	}

	if config, ok := SimDBConfigs[service]; ok {
		LogDebug("Using preset DB config for service: %s", service)
		return config, true
	}

	return DBConfig{}, false
}

// GetDBConfigForDataset gets DB config specifically for a dataset from plato-config.yml
func GetDBConfigForDataset(service string, dataset string) (DBConfig, bool) {
	// Try to get from plato-config.yml for the specific dataset
	if config, ok := GetDBConfigFromPlatoConfig(dataset); ok {
		LogDebug("Using DB config from plato-config.yml for service: %s, dataset: %s", service, dataset)
		return config, true
	}

	// Fall back to the original GetDBConfig logic
	return GetDBConfig(service)
}

// OpenTemporaryProxytunnel opens a proxytunnel for the duration of a cleanup operation
func OpenTemporaryProxytunnel(baseURL, publicID string, remotePort int) (*exec.Cmd, int, error) {
	LogDebug("Opening temporary proxytunnel for port %d", remotePort)

	// Get proxy configuration to log it
	proxyConfig := sdkutils.GetProxyConfig(baseURL)
	LogDebug("Using proxy server: %s (secure: %v)", proxyConfig.Server, proxyConfig.Secure)

	cmd, localPort, err := sdkutils.OpenTemporaryProxytunnel(baseURL, publicID, remotePort)
	if err != nil {
		return nil, 0, err
	}

	LogDebug("Temporary proxytunnel started with PID: %d on localhost:%d", cmd.Process.Pid, localPort)
	return cmd, localPort, nil
}

// CloseTemporaryProxytunnel closes a temporary proxytunnel
func CloseTemporaryProxytunnel(cmd *exec.Cmd) {
	if cmd != nil && cmd.Process != nil {
		LogDebug("Closing temporary proxytunnel PID: %d", cmd.Process.Pid)
		sdkutils.CloseTemporaryProxytunnel(cmd)
	}
}

// ClearAuditLog connects to the database and clears the audit_log table
func ClearAuditLog(dbConfig DBConfig, localPort int) error {
	LogDebug("Clearing audit_log from %s database on localhost:%d", dbConfig.DBType, localPort)

	// Convert CLI DBConfig to SDK DBConfig
	sdkDBConfig := sdkutils.DBConfig{
		DBType:    dbConfig.DBType,
		User:      dbConfig.User,
		Password:  dbConfig.Password,
		DestPort:  dbConfig.DestPort,
		Databases: dbConfig.Databases,
	}

	err := sdkutils.ClearAuditLog(sdkDBConfig, localPort)
	if err != nil {
		LogDebug("Warning: failed to clear audit_log: %v", err)
		return err
	}

	LogDebug("Successfully cleared audit_log from database(s)")
	return nil
}

// ClearEnvState calls the /env/{job_group_id}/state endpoint to clear cache
func ClearEnvState(client *plato.PlatoClient, jobGroupID string) error {
	LogDebug("Clearing env state for job group: %s", jobGroupID)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req, err := client.NewRequest(ctx, "GET", fmt.Sprintf("/env/%s/state", jobGroupID), nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to call /env/state: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("/env/state returned status %d", resp.StatusCode)
	}

	LogDebug("Successfully cleared env state")
	return nil
}

// PreSnapshotCleanup performs database cleanup and cache clearing before snapshot
// Returns (needsDBConfig, error) - needsDBConfig=true means manual entry is required
func PreSnapshotCleanup(client *plato.PlatoClient, publicID, jobGroupID, service, dataset string) (bool, error) {
	LogDebug("Starting pre-snapshot cleanup for service: %s, dataset: %s", service, dataset)

	// Try to get DB config for the specific dataset first
	dbConfig, ok := GetDBConfigForDataset(service, dataset)
	if !ok {
		LogDebug("No DB config found for service: %s, dataset: %s, manual entry required", service, dataset)
		return true, nil
	}

	tunnelCmd, localPort, err := OpenTemporaryProxytunnel(client.GetBaseURL(), publicID, dbConfig.DestPort)
	if err != nil {
		return false, fmt.Errorf("failed to open proxytunnel: %w", err)
	}
	defer CloseTemporaryProxytunnel(tunnelCmd)

	if err := ClearAuditLog(dbConfig, localPort); err != nil {
		LogDebug("Warning: failed to clear audit_log: %v", err)
	}

	if err := ClearEnvState(client, jobGroupID); err != nil {
		return false, fmt.Errorf("failed to clear env state: %w", err)
	}

	LogDebug("Pre-snapshot cleanup completed successfully")
	return false, nil
}

// PreSnapshotCleanupWithConfig performs cleanup with a provided DB config
func PreSnapshotCleanupWithConfig(client *plato.PlatoClient, publicID, jobGroupID string, dbConfig DBConfig) error {
	LogDebug("Starting pre-snapshot cleanup with provided config")

	tunnelCmd, localPort, err := OpenTemporaryProxytunnel(client.GetBaseURL(), publicID, dbConfig.DestPort)
	if err != nil {
		return fmt.Errorf("failed to open proxytunnel: %w", err)
	}
	defer CloseTemporaryProxytunnel(tunnelCmd)

	if err := ClearAuditLog(dbConfig, localPort); err != nil {
		LogDebug("Warning: failed to clear audit_log: %v", err)
	}

	if err := ClearEnvState(client, jobGroupID); err != nil {
		return fmt.Errorf("failed to clear env state: %w", err)
	}

	LogDebug("Pre-snapshot cleanup completed successfully")
	return nil
}
