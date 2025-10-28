package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	plato "plato-sdk"
	"plato-cli/internal/utils"

	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
)

type DBConfig struct {
	DBType    string   `json:"db_type"`
	User      string   `json:"user"`
	Password  string   `json:"password"`
	DestPort  int      `json:"dest_port"`
	Databases []string `json:"databases"`
}

var simDBConfigs = map[string]DBConfig{
	// PostgreSQL
	"bugsink":     {DBType: "postgresql", User: "bugsink", Password: "bugsink_password", DestPort: 5432, Databases: []string{"postgres", "bugsink"}},
	"calcom":      {DBType: "postgresql", User: "unicorn_user", Password: "magical_password", DestPort: 5432, Databases: []string{"postgres", "calendso"}},
	"discourse":   {DBType: "postgresql", User: "discourse", Password: "discourse", DestPort: 5432, Databases: []string{"postgres", "discourse"}},
	"espocrm":     {DBType: "postgresql", User: "espocrm", Password: "espocrm", DestPort: 5432, Databases: []string{"postgres", "espocrm"}},
	"firefly":     {DBType: "postgresql", User: "firefly", Password: "password", DestPort: 5432, Databases: []string{"postgres", "firefly"}},
	"gitlab":      {DBType: "postgresql", User: "gitlab", Password: "changeme1234", DestPort: 5432, Databases: []string{"postgres", "gitlabhq_production"}},
	"grafana":     {DBType: "postgresql", User: "grafanauser", Password: "grafanapassword", DestPort: 5432, Databases: []string{"postgres", "grafanadb", "pagila"}},
	"listmonk":    {DBType: "postgresql", User: "listmonk", Password: "listmonk", DestPort: 5432, Databases: []string{"postgres", "listmonk"}},
	"mattermost":  {DBType: "postgresql", User: "mmuser", Password: "mmuser_password", DestPort: 5432, Databases: []string{"postgres", "mattermost"}},
	"mealie":      {DBType: "postgresql", User: "mealie", Password: "mealie", DestPort: 5432, Databases: []string{"postgres", "mealie"}},
	"metabase":    {DBType: "postgresql", User: "metabase", Password: "metabase", DestPort: 5432, Databases: []string{"postgres", "metabase"}},
	"moodle":      {DBType: "postgresql", User: "moodle", Password: "moodle_password", DestPort: 5432, Databases: []string{"postgres", "moodle"}},
	"odoo":        {DBType: "postgresql", User: "odoo", Password: "myodoo", DestPort: 5432, Databases: []string{"postgres", "odoo_db"}},
	"openproject": {DBType: "postgresql", User: "postgres", Password: "p4ssw0rd", DestPort: 5432, Databases: []string{"postgres", "openproject"}},
	"outline":     {DBType: "postgresql", User: "outline", Password: "outline", DestPort: 5432, Databases: []string{"postgres", "outline"}},
	"paperless":   {DBType: "postgresql", User: "paperless", Password: "paperless", DestPort: 5432, Databases: []string{"postgres", "paperless"}},
	"roundcube":   {DBType: "postgresql", User: "roundcube", Password: "roundcube", DestPort: 5432, Databases: []string{"postgres", "dbmail"}},
	"taiga":       {DBType: "postgresql", User: "taiga", Password: "taiga", DestPort: 5432, Databases: []string{"postgres", "taiga"}},
	"twenty":      {DBType: "postgresql", User: "postgres", Password: "mysecurepass123", DestPort: 5432, Databases: []string{"postgres", "default"}},

	// MySQL/MariaDB
	"dolibarr":      {DBType: "mysql", User: "root", Password: "root", DestPort: 3306, Databases: []string{"dolibarr"}},
	"frappebuilder": {DBType: "mysql", User: "root", Password: "admin", DestPort: 3306, Databases: []string{"admin", "frappebuilder_sim"}},
	"frappecrm":     {DBType: "mysql", User: "root", Password: "admin", DestPort: 3306, Databases: []string{"admin", "frappecrm_sim"}},
	"kanboard":      {DBType: "mysql", User: "root", Password: "secret", DestPort: 3306, Databases: []string{"kanboard"}},
	"nextcloud":     {DBType: "mysql", User: "root", Password: "changeme1234", DestPort: 3306, Databases: []string{"nextcloud"}},
	"opencart":      {DBType: "mysql", User: "root", Password: "bitnami", DestPort: 3306, Databases: []string{"bitnami_opencart"}},
	"photoprism":    {DBType: "mysql", User: "root", Password: "photoprism", DestPort: 3306, Databases: []string{"photoprism"}},
	"redmine":       {DBType: "mysql", User: "root", Password: "example", DestPort: 3306, Databases: []string{"redmine"}},
	"snipeit":       {DBType: "mysql", User: "root", Password: "changeme1234", DestPort: 3306, Databases: []string{"snipeit"}},
	"suitecrm":      {DBType: "mysql", User: "root", Password: "bitnami123", DestPort: 3306, Databases: []string{"bitnami_suitecrm"}},
	"vikunja":       {DBType: "mysql", User: "root", Password: "supersecret", DestPort: 3306, Databases: []string{"vikunja"}},
}

// getCustomDBConfigPath returns the path to the custom DB configs file
func getCustomDBConfigPath() string {
	homeDir := os.Getenv("HOME")
	return filepath.Join(homeDir, ".plato", "custom_db_configs.json")
}

// loadCustomDBConfigs loads user-defined DB configs from file
func loadCustomDBConfigs() map[string]DBConfig {
	customConfigs := make(map[string]DBConfig)

	path := getCustomDBConfigPath()
	data, err := os.ReadFile(path)
	if err != nil {
		// File doesn't exist yet, return empty map
		return customConfigs
	}

	if err := json.Unmarshal(data, &customConfigs); err != nil {
		logDebug("Failed to parse custom DB configs: %v", err)
		return customConfigs
	}

	logDebug("Loaded %d custom DB configs", len(customConfigs))
	return customConfigs
}

// saveCustomDBConfig saves a new custom DB config to file
func saveCustomDBConfig(service string, config DBConfig) error {
	// Load existing configs
	customConfigs := loadCustomDBConfigs()

	// Add/update the new config
	customConfigs[service] = config

	// Ensure directory exists
	configDir := filepath.Dir(getCustomDBConfigPath())
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	// Marshal to JSON
	data, err := json.MarshalIndent(customConfigs, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal configs: %w", err)
	}

	// Write to file
	if err := os.WriteFile(getCustomDBConfigPath(), data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	logDebug("Saved custom DB config for service: %s", service)
	return nil
}

// getDBConfig gets DB config for a service, checking custom configs first, then presets
func getDBConfig(service string) (DBConfig, bool) {
	// First check custom configs
	customConfigs := loadCustomDBConfigs()
	if config, ok := customConfigs[service]; ok {
		logDebug("Using custom DB config for service: %s", service)
		return config, true
	}

	// Fall back to preset configs
	if config, ok := simDBConfigs[service]; ok {
		logDebug("Using preset DB config for service: %s", service)
		return config, true
	}

	return DBConfig{}, false
}

// Add all Odoo variants
func init() {
	odooVariants := []string{
		"odooattendances", "odoocrm", "odoodatarecycle", "odooelearning",
		"odooemailmarketing", "odooemployees", "odooevents", "odooexpenses",
		"odoofleet", "odooinventory", "odooinvoicing", "odoolivechat",
		"odoolunch", "odoomaintenance", "odoomanufacturing", "odoopos",
		"odoopurchase", "odoorecruitment", "odoorepairs", "odoorestaurant",
		"odoosales", "odoosmsmarketing", "odoosurveys", "odootimeoff", "odootodo",
	}
	for _, variant := range odooVariants {
		simDBConfigs[variant] = DBConfig{
			DBType:    "postgresql",
			User:      "odoo",
			Password:  "myodoo",
			DestPort:  5432,
			Databases: []string{"postgres", "odoo_db"},
		}
	}
	// Add Frappe variants
	frappeVariants := []string{
		"frappeeducation", "frappeerpnext", "frappehelpdesk",
		"frappeinsights", "frappelms", "frappewiki",
	}
	for _, variant := range frappeVariants {
		dbName := variant + "_sim"
		if variant == "frappeerpnext" {
			simDBConfigs[variant] = DBConfig{
				DBType:    "mysql",
				User:      "root",
				Password:  "admin",
				DestPort:  3306,
				Databases: []string{"admin"},
			}
		} else {
			simDBConfigs[variant] = DBConfig{
				DBType:    "mysql",
				User:      "root",
				Password:  "admin",
				DestPort:  3306,
				Databases: []string{"admin", dbName},
			}
		}
	}
}

// openTemporaryProxytunnel opens a proxytunnel for the duration of a cleanup operation
func openTemporaryProxytunnel(publicID string, remotePort int) (*exec.Cmd, int, error) {
	logDebug("Opening temporary proxytunnel for port %d", remotePort)

	// Try to use the same port as remote
	localPort, err := utils.FindFreePortPreferred(remotePort)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to find free port: %w", err)
	}

	proxytunnelPath, err := utils.FindProxytunnelPath()
	if err != nil {
		return nil, 0, fmt.Errorf("proxytunnel not found: %w", err)
	}

	cmd := exec.Command(
		proxytunnelPath,
		"-E",
		"-p", "proxy.plato.so:9000",
		"-P", fmt.Sprintf("%s@%d:newpass", publicID, remotePort),
		"-d", fmt.Sprintf("127.0.0.1:%d", remotePort),
		"-a", fmt.Sprintf("%d", localPort),
		"-v",
		"--no-check-certificate",
	)

	if err := cmd.Start(); err != nil {
		return nil, 0, fmt.Errorf("failed to start proxytunnel: %w", err)
	}

	logDebug("Temporary proxytunnel started with PID: %d on localhost:%d", cmd.Process.Pid, localPort)

	// Give the tunnel a moment to establish
	time.Sleep(500 * time.Millisecond)

	return cmd, localPort, nil
}

// closeTemporaryProxytunnel closes a temporary proxytunnel
func closeTemporaryProxytunnel(cmd *exec.Cmd) {
	if cmd != nil && cmd.Process != nil {
		logDebug("Closing temporary proxytunnel PID: %d", cmd.Process.Pid)
		cmd.Process.Kill()
		go cmd.Wait()
	}
}

// clearAuditLog connects to the database and clears the audit_log table
func clearAuditLog(dbConfig DBConfig, localPort int) error {
	logDebug("Clearing audit_log from %s database on localhost:%d", dbConfig.DBType, localPort)

	var db *sql.DB
	var err error
	clearedCount := 0

	if dbConfig.DBType == "postgresql" {
		// Try each database and clear audit_log if it exists
		for _, dbName := range dbConfig.Databases {
			connStr := fmt.Sprintf("host=127.0.0.1 port=%d user=%s password=%s dbname=%s sslmode=disable",
				localPort, dbConfig.User, dbConfig.Password, dbName)

			db, err = sql.Open("postgres", connStr)
			if err != nil {
				logDebug("Failed to connect to postgres db %s: %v", dbName, err)
				continue
			}

			// Test connection
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)

			if err = db.PingContext(ctx); err != nil {
				logDebug("Failed to ping postgres db %s: %v", dbName, err)
				cancel()
				db.Close()
				continue
			}

			// Try to truncate audit_log (PostgreSQL)
			_, err = db.ExecContext(ctx, "TRUNCATE TABLE public.audit_log RESTART IDENTITY CASCADE")
			if err == nil {
				logDebug("Successfully truncated audit_log from postgres db: %s", dbName)
				clearedCount++
			} else {
				logDebug("No audit_log in %s (or error): %v", dbName, err)
			}
			cancel()
			db.Close()
		}
	} else if dbConfig.DBType == "mysql" {
		// Try each database and clear audit_log if it exists
		for _, dbName := range dbConfig.Databases {
			dsn := fmt.Sprintf("%s:%s@tcp(127.0.0.1:%d)/%s",
				dbConfig.User, dbConfig.Password, localPort, dbName)

			db, err = sql.Open("mysql", dsn)
			if err != nil {
				logDebug("Failed to connect to mysql db %s: %v", dbName, err)
				continue
			}

			// Test connection
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)

			if err = db.PingContext(ctx); err != nil {
				logDebug("Failed to ping mysql db %s: %v", dbName, err)
				cancel()
				db.Close()
				continue
			}

			// Try to truncate audit.audit_log (MySQL) - disable foreign key checks
			_, err = db.ExecContext(ctx, "SET FOREIGN_KEY_CHECKS = 0")
			if err != nil {
				logDebug("Failed to disable foreign key checks in %s: %v", dbName, err)
				cancel()
				db.Close()
				continue
			}

			_, err = db.ExecContext(ctx, "DELETE FROM `audit_log`")
			if err != nil {
				logDebug("Failed to truncate audit_log in %s: %v", dbName, err)
				// Re-enable foreign key checks before continuing
				db.ExecContext(ctx, "SET FOREIGN_KEY_CHECKS = 1")
				cancel()
				db.Close()
				continue
			}

			// Re-enable foreign key checks
			_, err = db.ExecContext(ctx, "SET FOREIGN_KEY_CHECKS = 1")
			if err != nil {
				logDebug("Warning: failed to re-enable foreign key checks in %s: %v", dbName, err)
			}

			logDebug("Successfully truncated audit.audit_log from mysql db: %s", dbName)
			clearedCount++
			cancel()
			db.Close()
		}
	}

	if clearedCount == 0 {
		return fmt.Errorf("could not find or clear audit_log table in any database")
	}

	logDebug("Successfully cleared audit_log from %d database(s)", clearedCount)
	return nil
}

// clearEnvState calls the /env/{job_group_id}/state endpoint to clear cache
func clearEnvState(client *plato.PlatoClient, jobGroupID string) error {
	logDebug("Clearing env state for job group: %s", jobGroupID)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Use the authenticated client to make the request
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

	logDebug("Successfully cleared env state")
	return nil
}

// preSnapshotCleanup performs database cleanup and cache clearing before snapshot
// Returns (needsDBConfig, error) - needsDBConfig=true means manual entry is required
func preSnapshotCleanup(client *plato.PlatoClient, publicID, jobGroupID, service string) (bool, error) {
	logDebug("Starting pre-snapshot cleanup for service: %s", service)

	// Get DB config for this service (checks custom then preset)
	dbConfig, ok := getDBConfig(service)
	if !ok {
		logDebug("No DB config found for service: %s, manual entry required", service)
		return true, nil
	}

	// Open temporary proxytunnel
	tunnelCmd, localPort, err := openTemporaryProxytunnel(publicID, dbConfig.DestPort)
	if err != nil {
		return false, fmt.Errorf("failed to open proxytunnel: %w", err)
	}
	defer closeTemporaryProxytunnel(tunnelCmd)

	// Clear audit_log
	if err := clearAuditLog(dbConfig, localPort); err != nil {
		logDebug("Warning: failed to clear audit_log: %v", err)
		// Don't fail the whole operation if audit_log doesn't exist
	}

	// Clear env state
	if err := clearEnvState(client, jobGroupID); err != nil {
		return false, fmt.Errorf("failed to clear env state: %w", err)
	}

	logDebug("Pre-snapshot cleanup completed successfully")
	return false, nil
}

// preSnapshotCleanupWithConfig performs cleanup with a provided DB config
func preSnapshotCleanupWithConfig(client *plato.PlatoClient, publicID, jobGroupID string, dbConfig DBConfig) error {
	logDebug("Starting pre-snapshot cleanup with provided config")

	// Open temporary proxytunnel
	tunnelCmd, localPort, err := openTemporaryProxytunnel(publicID, dbConfig.DestPort)
	if err != nil {
		return fmt.Errorf("failed to open proxytunnel: %w", err)
	}
	defer closeTemporaryProxytunnel(tunnelCmd)

	// Clear audit_log
	if err := clearAuditLog(dbConfig, localPort); err != nil {
		logDebug("Warning: failed to clear audit_log: %v", err)
		// Don't fail the whole operation if audit_log doesn't exist
	}

	// Clear env state
	if err := clearEnvState(client, jobGroupID); err != nil {
		return fmt.Errorf("failed to clear env state: %w", err)
	}

	logDebug("Pre-snapshot cleanup completed successfully")
	return nil
}
