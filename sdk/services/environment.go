package services

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"plato-sdk/models"
)

type EnvironmentService struct {
	client ClientInterface
}

func NewEnvironmentService(client ClientInterface) *EnvironmentService {
	return &EnvironmentService{
		client: client,
	}
}

// MakeOptions contains options for creating an environment
type MakeOptions struct {
	ArtifactID            *string
	Tag                   *string
	Dataset               *string
	Alias                 *string
	Version               *string
	InterfaceType         string
	OpenPageOnStart       bool
	ViewportWidth         int
	ViewportHeight        int
	RecordNetworkRequests bool
	RecordActions         bool
	Keepalive             bool
	Fast                  bool
	EnvConfig             map[string]interface{}
}

// DefaultMakeOptions returns MakeOptions with default values matching Python SDK
func DefaultMakeOptions() *MakeOptions {
	return &MakeOptions{
		InterfaceType:         "browser",
		OpenPageOnStart:       false,
		ViewportWidth:         1920,
		ViewportHeight:        1080,
		RecordNetworkRequests: false,
		RecordActions:         false,
		Keepalive:             false,
		Fast:                  false,
		EnvConfig:             make(map[string]interface{}),
	}
}

// Make creates a new environment using the /env/make2 endpoint (mirrors Python SDK)
func (s *EnvironmentService) Make(ctx context.Context, envID string, opts *MakeOptions) (*models.Environment, error) {
	if opts == nil {
		opts = DefaultMakeOptions()
	}

	// Default to "noop" interface type like Python SDK does
	interfaceType := opts.InterfaceType
	if interfaceType == "" {
		interfaceType = "noop"
	}

	payload := map[string]interface{}{
		"env_id":                  envID,
		"interface_type":          interfaceType,
		"interface_width":         opts.ViewportWidth,
		"interface_height":        opts.ViewportHeight,
		"source":                  "SDK",
		"open_page_on_start":      opts.OpenPageOnStart,
		"record_network_requests": opts.RecordNetworkRequests,
		"record_actions":          opts.RecordActions,
		"keepalive":               opts.Keepalive,
		"fast":                    opts.Fast,
		"env_config":              opts.EnvConfig,
	}

	if opts.ArtifactID != nil {
		payload["artifact_id"] = *opts.ArtifactID
	}
	if opts.Tag != nil {
		payload["tag"] = *opts.Tag
	}
	if opts.Dataset != nil {
		payload["dataset"] = *opts.Dataset
	}
	if opts.Alias != nil {
		payload["alias"] = *opts.Alias
	}
	if opts.Version != nil {
		payload["version"] = *opts.Version
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := s.client.NewRequest(ctx, "POST", "/env/make2", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response body for logging
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	fmt.Printf("Make response (status %d): %s\n", resp.StatusCode, string(bodyBytes))

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var makeResp struct {
		JobID string  `json:"job_id"`
		Alias *string `json:"alias"`
	}
	if err := json.Unmarshal(bodyBytes, &makeResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	fmt.Printf("Decoded JobID: %s, Alias: %v\n", makeResp.JobID, makeResp.Alias)

	env := &models.Environment{
		JobID: makeResp.JobID,
		EnvID: envID,
	}
	if makeResp.Alias != nil {
		env.Alias = *makeResp.Alias
	}

	return env, nil
}

// GetJobStatus retrieves the status of a job
func (s *EnvironmentService) GetJobStatus(ctx context.Context, jobID string) (*models.JobStatus, error) {
	req, err := s.client.NewRequest(ctx, "GET", fmt.Sprintf("/env/%s/status", jobID), nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response body for logging
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	fmt.Printf("GetJobStatus response (status %d): %s\n", resp.StatusCode, string(bodyBytes))

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var status models.JobStatus
	if err := json.Unmarshal(bodyBytes, &status); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	fmt.Printf("Job status: %s\n", status.Status)

	return &status, nil
}

// GetWorkerReady checks if the worker for a job is ready
func (s *EnvironmentService) GetWorkerReady(ctx context.Context, jobID string) (*models.WorkerStatus, error) {
	req, err := s.client.NewRequest(ctx, "GET", fmt.Sprintf("/env/%s/worker_ready", jobID), nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response body for logging
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	fmt.Printf("GetWorkerReady response (status %d): %s\n", resp.StatusCode, string(bodyBytes))

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var status models.WorkerStatus
	if err := json.Unmarshal(bodyBytes, &status); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	fmt.Printf("Worker ready: %v, Error: %v\n", status.Ready, status.Error)

	return &status, nil
}

// Reset resets an environment and creates a new run session
func (s *EnvironmentService) Reset(ctx context.Context, jobID string) (*models.ResetResponse, error) {
	payload := map[string]interface{}{}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := s.client.NewRequest(ctx, "POST", fmt.Sprintf("/env/%s/reset", jobID), bytes.NewReader(body))
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response body for logging
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	fmt.Printf("Reset response (status %d): %s\n", resp.StatusCode, string(bodyBytes))

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var resetResp models.ResetResponse
	if err := json.Unmarshal(bodyBytes, &resetResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	fmt.Printf("Reset success: %v, RunSessionID: %s\n", resetResp.Success, resetResp.Data.RunSessionID)

	return &resetResp, nil
}

// Close closes an environment
func (s *EnvironmentService) Close(ctx context.Context, jobID string) error {
	req, err := s.client.NewRequest(ctx, "POST", fmt.Sprintf("/env/%s/close", jobID), nil)
	if err != nil {
		return err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}
