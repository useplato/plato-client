// Package services provides the sandbox service for Plato API operations.
//
// This file implements the SandboxService which handles full VM sandbox operations
// including creating VMs from simulator configurations, setting up sandboxes with
// datasets, monitoring operations via SSE streams, managing snapshots, and starting
// Plato workers. Sandboxes are isolated VM environments used for building and
// testing simulators before they are versioned and deployed.
package services

import (
	"bufio"
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"strings"
	"time"

	"plato-sdk/models"
	"plato-sdk/utils"

	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
)

// ClientInterface defines the methods needed from PlatoClient
type ClientInterface interface {
	NewRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error)
	NewHubRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error)
	Do(req *http.Request) (*http.Response, error)
	GetBaseURL() string
}

type SandboxService struct {
	client ClientInterface
}

func NewSandboxService(client ClientInterface) *SandboxService {
	return &SandboxService{
		client: client,
	}
}

// Create creates a new sandbox from a full SimConfigDataset configuration
func (s *SandboxService) Create(ctx context.Context, config *models.SimConfigDataset, dataset, alias string, artifactID *string, service string, timeout *int) (*models.Sandbox, error) {
	// Marshal config to JSON
	configJSON, err := json.Marshal(config)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal config: %w", err)
	}

	// Unmarshal to map for payload construction
	var configMap map[string]interface{}
	if err := json.Unmarshal(configJSON, &configMap); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	payload := map[string]interface{}{
		"dataset":              dataset,
		"plato_dataset_config": configMap,
		"wait_time":            600,
		"alias":                alias,
	}

	// Only include timeout if provided, otherwise server will use default
	if timeout != nil {
		payload["sandbox_timeout"] = *timeout
	}

	if artifactID != nil {
		payload["artifact_id"] = *artifactID
	}

	if service != "" {
		payload["service"] = service
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := s.client.NewRequest(ctx, "POST", "/public-build/vm/create", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)

		// Try to parse as JSON error response
		var errResp struct {
			Error   string `json:"error"`
			Message string `json:"message"`
			Detail  string `json:"detail"`
		}
		if err := json.Unmarshal(bodyBytes, &errResp); err == nil {
			// Use structured error message if available
			if errResp.Error != "" {
				return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, errResp.Error)
			}
			if errResp.Message != "" {
				return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, errResp.Message)
			}
			if errResp.Detail != "" {
				return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, errResp.Detail)
			}
		}

		// Fallback to raw body
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var createResp struct {
		URL           string `json:"url"`
		PublicID      string `json:"job_public_id"`
		JobGroupID    string `json:"job_group_id"`
		Status        string `json:"status"`
		CorrelationID string `json:"correlation_id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&createResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	// Map to Sandbox model
	sandbox := &models.Sandbox{
		PublicId:      createResp.PublicID,
		JobGroupId:    createResp.JobGroupID,
		Url:           createResp.URL,
		Status:        createResp.Status,
		CorrelationId: createResp.CorrelationID,
	}

	return sandbox, nil
}

// MonitorOperationWithEvents monitors an SSE stream and sends event details to a channel
func (s *SandboxService) MonitorOperationWithEvents(ctx context.Context, correlationID string, timeout time.Duration, eventChan chan<- string) error {
	req, err := s.client.NewRequest(ctx, "GET", fmt.Sprintf("/public-build/events/%s", correlationID), nil)
	if err != nil {
		return fmt.Errorf("failed to create SSE request: %w", err)
	}

	// Set timeout on context
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	req = req.WithContext(ctx)

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("SSE request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("SSE connection failed (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	// Read SSE stream
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()

		// SSE format: "data: <json>"
		if strings.HasPrefix(line, "data: ") {
			jsonData := strings.TrimPrefix(line, "data: ")

			// Parse JSON
			var event struct {
				Type    string `json:"type"`
				Success bool   `json:"success"`
				Error   string `json:"error"`
				Message string `json:"message"`
			}
			if err := json.Unmarshal([]byte(jsonData), &event); err != nil {
				eventChan <- fmt.Sprintf("[DEBUG] Failed to parse JSON: %v, data: %s", err, jsonData)
				continue // Skip malformed JSON
			}

			eventChan <- fmt.Sprintf("[DEBUG] Received event - Type: %s, Success: %v, Message: %s", event.Type, event.Success, event.Message)

			// Send event message to channel if available
			// Send both message and type information
			if event.Message != "" {
				eventChan <- event.Message
			} else if event.Type != "" && event.Type != "connected" {
				// If no message but we have a type, send that
				eventChan <- fmt.Sprintf("[%s]", event.Type)
			}

			// Handle different event types
			switch event.Type {
			case "connected":
				// Initial connection, continue listening
				eventChan <- "[DEBUG] SSE connected"
				continue
			case "error":
				// Error event
				eventChan <- fmt.Sprintf("[DEBUG] Error event: %s", event.Error)
				errorMsg := event.Error
				if errorMsg == "" {
					errorMsg = event.Message
				}
				return fmt.Errorf("operation error: %s", errorMsg)
			default:
				// Handle all other event types by checking success field
				eventChan <- fmt.Sprintf("[DEBUG] Event type=%s, success=%v", event.Type, event.Success)
				if event.Success {
					return nil // Success!
				}
				// Operation failed
				errorMsg := event.Error
				if errorMsg == "" {
					errorMsg = event.Message
				}
				if errorMsg == "" {
					errorMsg = "Operation failed"
				}
				return fmt.Errorf("operation failed: %s", errorMsg)
			}
		}
	}

	if err := scanner.Err(); err != nil {
		eventChan <- fmt.Sprintf("[DEBUG] Scanner error: %v", err)
		return fmt.Errorf("error reading SSE stream: %w", err)
	}

	eventChan <- "[DEBUG] SSE stream ended without receiving completion event"
	return fmt.Errorf("SSE stream ended without completion")
}

// MonitorOperation monitors an SSE stream for operation completion
func (s *SandboxService) MonitorOperation(ctx context.Context, correlationID string, timeout time.Duration) error {
	req, err := s.client.NewRequest(ctx, "GET", fmt.Sprintf("/public-build/events/%s", correlationID), nil)
	if err != nil {
		return fmt.Errorf("failed to create SSE request: %w", err)
	}

	// Set timeout on context
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	req = req.WithContext(ctx)

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("SSE request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("SSE connection failed (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	// Read SSE stream
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()

		// SSE format: "data: <json>"
		if strings.HasPrefix(line, "data: ") {
			jsonData := strings.TrimPrefix(line, "data: ")

			// Parse JSON
			var event struct {
				Type    string `json:"type"`
				Success bool   `json:"success"`
				Error   string `json:"error"`
				Message string `json:"message"`
			}
			if err := json.Unmarshal([]byte(jsonData), &event); err != nil {
				continue // Skip malformed JSON
			}

			// Handle different event types
			switch event.Type {
			case "connected":
				// Initial connection, continue listening
				continue
			case "error":
				// Error event
				errorMsg := event.Error
				if errorMsg == "" {
					errorMsg = event.Message
				}
				return fmt.Errorf("operation error: %s", errorMsg)
			default:
				// Handle all other event types by checking success field
				if event.Success {
					return nil // Success!
				}
				// Operation failed
				errorMsg := event.Error
				if errorMsg == "" {
					errorMsg = event.Message
				}
				if errorMsg == "" {
					errorMsg = "Operation failed"
				}
				return fmt.Errorf("operation failed: %s", errorMsg)
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("error reading SSE stream: %w", err)
	}

	return fmt.Errorf("SSE stream ended without completion")
}

// SetupSandbox sets up a sandbox with optional SSH public key for plato user
func (s *SandboxService) SetupSandbox(ctx context.Context, jobID string, config *models.SimConfigDataset, dataset string, sshPublicKey string) (string, error) {
	// Marshal config to JSON
	configJSON, err := json.Marshal(config)
	if err != nil {
		return "", fmt.Errorf("failed to marshal config: %w", err)
	}

	// Unmarshal to map for payload construction
	var configMap map[string]interface{}
	if err := json.Unmarshal(configJSON, &configMap); err != nil {
		return "", fmt.Errorf("failed to unmarshal config: %w", err)
	}

	payload := map[string]interface{}{
		"dataset":              dataset,
		"plato_dataset_config": configMap,
	}

	// Add SSH public key if provided
	if sshPublicKey != "" {
		payload["ssh_public_key"] = sshPublicKey
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := s.client.NewRequest(ctx, "POST", fmt.Sprintf("/public-build/vm/%s/setup-sandbox", jobID), bytes.NewReader(body))
	if err != nil {
		return "", err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusAccepted {
		bodyBytes, _ := io.ReadAll(resp.Body)

		// Try to parse as JSON error response
		var errResp struct {
			Error   string `json:"error"`
			Message string `json:"message"`
			Detail  []struct {
				Msg string        `json:"msg"`
				Loc []interface{} `json:"loc"`
			} `json:"detail"`
		}
		if err := json.Unmarshal(bodyBytes, &errResp); err == nil {
			// Use structured error message if available
			if errResp.Error != "" {
				return "", fmt.Errorf("%s", errResp.Error)
			}
			if errResp.Message != "" {
				return "", fmt.Errorf("%s", errResp.Message)
			}
			if len(errResp.Detail) > 0 {
				// Format validation errors nicely
				msg := errResp.Detail[0].Msg
				if len(errResp.Detail[0].Loc) > 0 {
					field := fmt.Sprintf("%v", errResp.Detail[0].Loc[len(errResp.Detail[0].Loc)-1])
					return "", fmt.Errorf("%s: %s", field, msg)
				}
				return "", fmt.Errorf("%s", msg)
			}
		}

		// Fallback to status code only if body is too long
		if len(bodyBytes) > 100 {
			return "", fmt.Errorf("API error %d", resp.StatusCode)
		}
		return "", fmt.Errorf("%s", string(bodyBytes))
	}

	// Parse the response to get correlation_id
	var setupResp struct {
		CorrelationID string `json:"correlation_id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&setupResp); err != nil {
		// If we can't parse the response, use the job ID as fallback
		return jobID, nil
	}

	return setupResp.CorrelationID, nil
}

// SendHeartbeat sends a heartbeat to keep the VM alive
func (s *SandboxService) SendHeartbeat(ctx context.Context, jobGroupID string) error {
	req, err := s.client.NewRequest(ctx, "POST", fmt.Sprintf("/env/%s/heartbeat", jobGroupID), nil)
	if err != nil {
		return err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("heartbeat request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("heartbeat failed (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}

// Get retrieves a sandbox by job ID
func (s *SandboxService) Get(ctx context.Context, jobID string) (*models.Sandbox, error) {
	req, err := s.client.NewRequest(ctx, "GET", fmt.Sprintf("/sandboxes/%s", jobID), nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var sandbox models.Sandbox
	if err := json.NewDecoder(resp.Body).Decode(&sandbox); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &sandbox, nil
}

// Delete deletes a sandbox by job ID
func (s *SandboxService) Delete(ctx context.Context, jobID string) error {
	req, err := s.client.NewRequest(ctx, "DELETE", fmt.Sprintf("/sandboxes/%s", jobID), nil)
	if err != nil {
		return err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return nil
}

// DeleteVM deletes a VM by public ID using the public-build endpoint
func (s *SandboxService) DeleteVM(ctx context.Context, publicID string) error {
	req, err := s.client.NewRequest(ctx, "DELETE", fmt.Sprintf("/public-build/vm/%s", publicID), nil)
	if err != nil {
		return err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to delete VM (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}

// List retrieves all sandboxes
func (s *SandboxService) List(ctx context.Context) ([]*models.Sandbox, error) {
	req, err := s.client.NewRequest(ctx, "GET", "/sandboxes", nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var sandboxes []*models.Sandbox
	if err := json.NewDecoder(resp.Body).Decode(&sandboxes); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return sandboxes, nil
}

// SetupRootPassword sets up root SSH access using a public key
func (s *SandboxService) SetupRootPassword(ctx context.Context, publicID, sshPublicKey string) error {
	payload := map[string]interface{}{
		"ssh_public_key": sshPublicKey,
		"timeout":        60,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := s.client.NewRequest(ctx, "POST", fmt.Sprintf("/public-build/vm/%s/setup-root-access", publicID), bytes.NewReader(body))
	if err != nil {
		return err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}

// CreateSnapshot creates a snapshot of a VM
func (s *SandboxService) CreateSnapshot(ctx context.Context, publicID string, req *models.CreateSnapshotRequest) (*models.CreateSnapshotResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := s.client.NewRequest(ctx, "POST", fmt.Sprintf("/public-build/vm/%s/snapshot", publicID), bytes.NewReader(body))
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted && resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var snapshotResp models.CreateSnapshotResponse
	if err := json.NewDecoder(resp.Body).Decode(&snapshotResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &snapshotResp, nil
}

// StartWorker starts the Plato worker and listeners on a VM
func (s *SandboxService) StartWorker(ctx context.Context, publicID string, req *models.StartWorkerRequest) (*models.StartWorkerResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := s.client.NewRequest(ctx, "POST", fmt.Sprintf("/public-build/vm/%s/start-worker", publicID), bytes.NewReader(body))
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted && resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var workerResp models.StartWorkerResponse
	if err := json.NewDecoder(resp.Body).Decode(&workerResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &workerResp, nil
}

// CreateSnapshotWithGit creates a snapshot with automatic git push and merge workflow
// If sourceDir is provided, it will:
// 1. Push code to Gitea on a timestamped branch
// 2. Merge that branch to main
// 3. Get the git hash
// 4. Create snapshot with that git hash
func (s *SandboxService) CreateSnapshotWithGit(ctx context.Context, publicID string, req *models.CreateSnapshotRequest, sourceDir string) (*models.CreateSnapshotResponse, error) {
	// Get Gitea service from the same client
	// We need to type assert to get access to the Gitea service
	type giteaClient interface {
		GetGiteaService() interface{}
	}

	// For now, just call CreateSnapshot without git workflow
	// The git workflow should be called explicitly by the user via C bindings
	return s.CreateSnapshot(ctx, publicID, req)
}

// SetupSSHAndGetInfo sets up SSH configuration for a sandbox and returns connection information
// This generates SSH keys, creates config file with proxy tunnel, uploads the public key, and returns connection details
func (s *SandboxService) SetupSSHAndGetInfo(ctx context.Context, baseURL string, localPort int, jobPublicID string, username string, config *models.SimConfigDataset, dataset string) (*models.SSHInfo, error) {
	// Use the utils.SetupSSHConfig function to generate keys and config
	sshHost, configPath, publicKey, privateKeyPath, err := utils.SetupSSHConfig(baseURL, localPort, jobPublicID, username)
	if err != nil {
		return nil, fmt.Errorf("failed to setup SSH: %w", err)
	}

	// Upload the public key to the sandbox via SetupSandbox API
	correlationID, err := s.SetupSandbox(ctx, jobPublicID, config, dataset, publicKey)
	if err != nil {
		return nil, fmt.Errorf("failed to upload SSH key to sandbox: %w", err)
	}

	// Build SSH command
	sshCommand := fmt.Sprintf("ssh -F %s %s", configPath, sshHost)

	return &models.SSHInfo{
		SSHCommand:     sshCommand,
		SSHHost:        sshHost,
		SSHConfigPath:  configPath,
		PublicID:       jobPublicID,
		PublicKey:      publicKey,
		PrivateKeyPath: privateKeyPath,
		CorrelationID:  correlationID,
	}, nil
}

// openTemporaryProxytunnel opens a temporary proxy tunnel for database access
func (s *SandboxService) openTemporaryProxytunnel(baseURL, publicID string, destPort int) (*exec.Cmd, int, error) {
	// Start the proxytunnel command
	localPort := 0 // Let it auto-assign a port
	cmd := exec.Command("proxytunnel", "start", baseURL, publicID, fmt.Sprintf("%d", destPort), fmt.Sprintf("%d", localPort))

	// Get stdout to read the assigned port
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, 0, fmt.Errorf("failed to get stdout: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return nil, 0, fmt.Errorf("failed to start proxytunnel: %w", err)
	}

	// Read the output to get the local port (proxytunnel prints it)
	scanner := bufio.NewScanner(stdout)
	if scanner.Scan() {
		line := scanner.Text()
		// Parse the port from output like "Tunnel started on localhost:12345"
		var port int
		if _, err := fmt.Sscanf(line, "Tunnel started on localhost:%d", &port); err == nil {
			localPort = port
		}
	}

	if localPort == 0 {
		localPort = 13306 // Default fallback port
	}

	time.Sleep(500 * time.Millisecond) // Give tunnel time to establish
	return cmd, localPort, nil
}

// closeTemporaryProxytunnel closes a temporary proxy tunnel
func (s *SandboxService) closeTemporaryProxytunnel(cmd *exec.Cmd) {
	if cmd != nil && cmd.Process != nil {
		cmd.Process.Kill()
		go cmd.Wait()
	}
}

// clearAuditLog connects to the database and clears the audit_log table
func (s *SandboxService) clearAuditLog(dbConfig models.DBConfig, localPort int) error {
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

// clearEnvState calls the /env/{job_group_id}/state endpoint to clear cache
func (s *SandboxService) clearEnvState(ctx context.Context, jobGroupID string) error {
	req, err := s.client.NewRequest(ctx, "GET", fmt.Sprintf("/env/%s/state", jobGroupID), nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to call /env/state: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("/env/state returned status %d", resp.StatusCode)
	}

	return nil
}

// CreateSnapshotWithCleanup creates a snapshot with pre-snapshot database cleanup
// This performs database cleanup (clears audit_log and env state) before creating the snapshot
func (s *SandboxService) CreateSnapshotWithCleanup(ctx context.Context, publicID, jobGroupID string, req *models.CreateSnapshotRequest, dbConfig *models.DBConfig) (*models.CreateSnapshotResponse, error) {
	// Step 1: Perform pre-snapshot cleanup if dbConfig is provided
	if dbConfig != nil {
		baseURL := s.client.GetBaseURL()

		// Open temporary proxy tunnel
		tunnelCmd, localPort, err := s.openTemporaryProxytunnel(baseURL, publicID, dbConfig.DestPort)
		if err != nil {
			return nil, fmt.Errorf("failed to open proxytunnel: %w", err)
		}
		defer s.closeTemporaryProxytunnel(tunnelCmd)

		// Clear audit log (best effort, don't fail if it doesn't exist)
		if err := s.clearAuditLog(*dbConfig, localPort); err != nil {
			// Log but don't fail - audit_log might not exist
		}

		// Clear env state
		if err := s.clearEnvState(ctx, jobGroupID); err != nil {
			return nil, fmt.Errorf("failed to clear env state: %w", err)
		}
	}

	// Step 2: Create the snapshot
	snapshotCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	return s.CreateSnapshot(snapshotCtx, publicID, req)
}
