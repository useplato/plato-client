// Package utils provides database utilities for database cleanup operations.
//
// This file handles database configuration, connection, and cleanup operations
// for pre-snapshot database maintenance tasks.
package utils

import (
	"context"
	"database/sql"
	"fmt"
	"os/exec"
	"time"

	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
)

// DBConfig represents database configuration for a simulator
type DBConfig struct {
	DBType    string   `json:"db_type"`
	User      string   `json:"user"`
	Password  string   `json:"password"`
	DestPort  int      `json:"dest_port"`
	Databases []string `json:"databases"`
}

// OpenTemporaryProxytunnel opens a proxytunnel for the duration of a cleanup operation
func OpenTemporaryProxytunnel(baseURL, publicID string, remotePort int) (*exec.Cmd, int, error) {
	localPort, err := FindFreePortPreferred(remotePort)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to find free port: %w", err)
	}

	proxytunnelPath, err := FindProxytunnelPath()
	if err != nil {
		return nil, 0, fmt.Errorf("proxytunnel not found: %w", err)
	}

	// Get proxy configuration based on base URL
	proxyConfig := GetProxyConfig(baseURL)

	// Build proxytunnel command arguments
	args := []string{}
	if proxyConfig.Secure {
		args = append(args, "-E")
	}
	args = append(args,
		"-p", proxyConfig.Server,
		"-P", fmt.Sprintf("%s@%d:newpass", publicID, remotePort),
		"-d", fmt.Sprintf("127.0.0.1:%d", remotePort),
		"-a", fmt.Sprintf("%d", localPort),
		"-v",
		"--no-check-certificate",
	)

	cmd := exec.Command(proxytunnelPath, args...)

	if err := cmd.Start(); err != nil {
		return nil, 0, fmt.Errorf("failed to start proxytunnel: %w", err)
	}

	// Give the tunnel time to establish
	time.Sleep(500 * time.Millisecond)

	return cmd, localPort, nil
}

// CloseTemporaryProxytunnel closes a temporary proxytunnel
func CloseTemporaryProxytunnel(cmd *exec.Cmd) {
	if cmd != nil && cmd.Process != nil {
		cmd.Process.Kill()
		go cmd.Wait()
	}
}

// ClearAuditLog connects to the database and clears the audit_log table
func ClearAuditLog(dbConfig DBConfig, localPort int) error {
	var db *sql.DB
	var err error
	clearedCount := 0

	if dbConfig.DBType == "postgresql" {
		for _, dbName := range dbConfig.Databases {
			connStr := fmt.Sprintf("host=127.0.0.1 port=%d user=%s password=%s dbname=%s sslmode=disable",
				localPort, dbConfig.User, dbConfig.Password, dbName)

			db, err = sql.Open("postgres", connStr)
			if err != nil {
				continue
			}

			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)

			if err = db.PingContext(ctx); err != nil {
				cancel()
				db.Close()
				continue
			}

			_, err = db.ExecContext(ctx, "TRUNCATE TABLE public.audit_log RESTART IDENTITY CASCADE")
			if err == nil {
				clearedCount++
			}
			cancel()
			db.Close()
		}
	} else if dbConfig.DBType == "mysql" {
		for _, dbName := range dbConfig.Databases {
			dsn := fmt.Sprintf("%s:%s@tcp(127.0.0.1:%d)/%s",
				dbConfig.User, dbConfig.Password, localPort, dbName)

			db, err = sql.Open("mysql", dsn)
			if err != nil {
				continue
			}

			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)

			if err = db.PingContext(ctx); err != nil {
				cancel()
				db.Close()
				continue
			}

			_, err = db.ExecContext(ctx, "SET FOREIGN_KEY_CHECKS = 0")
			if err != nil {
				cancel()
				db.Close()
				continue
			}

			_, err = db.ExecContext(ctx, "DELETE FROM `audit_log`")
			if err != nil {
				db.ExecContext(ctx, "SET FOREIGN_KEY_CHECKS = 1")
				cancel()
				db.Close()
				continue
			}

			db.ExecContext(ctx, "SET FOREIGN_KEY_CHECKS = 1")
			clearedCount++
			cancel()
			db.Close()
		}
	}

	if clearedCount == 0 {
		return fmt.Errorf("could not find or clear audit_log table in any database")
	}

	return nil
}
