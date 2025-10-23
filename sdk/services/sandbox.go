package services

import (
	"bufio"
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"plato-sdk/models"
)

// ClientInterface defines the methods needed from PlatoClient
type ClientInterface interface {
	NewRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error)
	Do(req *http.Request) (*http.Response, error)
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
func (s *SandboxService) Create(ctx context.Context, config models.SimConfigDataset, dataset, alias string, artifactID *string) (*models.Sandbox, error) {
	payload := map[string]interface{}{
		"dataset":              dataset,
		"plato_dataset_config": config,
		"timeout":              1200,
		"wait_time":            600,
		"alias":                alias,
	}

	if artifactID != nil {
		payload["artifact_id"] = *artifactID
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
		URL          string `json:"url"`
		PublicID     string `json:"job_public_id"`
		JobGroupID   string `json:"job_group_id"`
		Status       string `json:"status"`
		CorrelationID string `json:"correlation_id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&createResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	// Map to Sandbox model
	sandbox := &models.Sandbox{
		PublicID:      createResp.PublicID,
		JobGroupID:    createResp.JobGroupID,
		URL:           createResp.URL,
		Status:        createResp.Status,
		CorrelationID: createResp.CorrelationID,
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

		// SSE format: "data: <base64-encoded-json>"
		if strings.HasPrefix(line, "data: ") {
			encodedData := strings.TrimPrefix(line, "data: ")

			// Decode base64
			decodedData, err := base64.StdEncoding.DecodeString(encodedData)
			if err != nil {
				continue // Skip malformed data
			}

			// Parse JSON
			var event struct {
				Type    string `json:"type"`
				Success bool   `json:"success"`
				Error   string `json:"error"`
				Message string `json:"message"`
			}
			if err := json.Unmarshal(decodedData, &event); err != nil {
				continue // Skip malformed JSON
			}

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
				continue
			case "run_result", "ssh_result":
				// Operation completed
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
			case "error":
				// Error event
				errorMsg := event.Error
				if errorMsg == "" {
					errorMsg = event.Message
				}
				return fmt.Errorf("operation error: %s", errorMsg)
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("error reading SSE stream: %w", err)
	}

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

		// SSE format: "data: <base64-encoded-json>"
		if strings.HasPrefix(line, "data: ") {
			encodedData := strings.TrimPrefix(line, "data: ")

			// Decode base64
			decodedData, err := base64.StdEncoding.DecodeString(encodedData)
			if err != nil {
				continue // Skip malformed data
			}

			// Parse JSON
			var event struct {
				Type    string `json:"type"`
				Success bool   `json:"success"`
				Error   string `json:"error"`
				Message string `json:"message"`
			}
			if err := json.Unmarshal(decodedData, &event); err != nil {
				continue // Skip malformed JSON
			}

			// Handle different event types
			switch event.Type {
			case "connected":
				// Initial connection, continue listening
				continue
			case "run_result", "ssh_result":
				// Operation completed
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
			case "error":
				// Error event
				errorMsg := event.Error
				if errorMsg == "" {
					errorMsg = event.Message
				}
				return fmt.Errorf("operation error: %s", errorMsg)
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("error reading SSE stream: %w", err)
	}

	return fmt.Errorf("SSE stream ended without completion")
}

// SetupSandbox sets up a sandbox
func (s *SandboxService) SetupSandbox(ctx context.Context, jobID string, config models.SimConfigDataset, dataset string) (string, error) {
	payload := map[string]interface{}{
		"dataset":              dataset,
		"plato_dataset_config": config,
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
				Msg string `json:"msg"`
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
