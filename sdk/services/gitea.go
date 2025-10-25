// Package services provides the Gitea service for Plato API operations.
//
// This file implements the GiteaService which handles Gitea integration operations
// including retrieving authentication credentials, listing simulators with repository
// information, and managing simulator repositories. Gitea is the git hosting platform
// used by Plato for storing and versioning simulator source code.
package services

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"plato-sdk/models"
)

// GiteaService handles Gitea-related API operations
type GiteaService struct {
	client ClientInterface
}

// NewGiteaService creates a new Gitea service
func NewGiteaService(client ClientInterface) *GiteaService {
	return &GiteaService{client: client}
}

// GetCredentials retrieves Gitea credentials for the organization
func (s *GiteaService) GetCredentials(ctx context.Context) (*models.GiteaCredentials, error) {
	req, err := s.client.NewHubRequest(ctx, "GET", "/gitea/credentials", nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var creds models.GiteaCredentials
	if err := json.NewDecoder(resp.Body).Decode(&creds); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &creds, nil
}

// ListSimulators lists all simulators with Gitea repository information
func (s *GiteaService) ListSimulators(ctx context.Context) ([]models.GiteaSimulator, error) {
	req, err := s.client.NewHubRequest(ctx, "GET", "/gitea/simulators", nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var simulators []models.GiteaSimulator
	if err := json.NewDecoder(resp.Body).Decode(&simulators); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return simulators, nil
}

// GetSimulatorRepository retrieves repository information for a simulator
func (s *GiteaService) GetSimulatorRepository(ctx context.Context, simulatorID int) (*models.GiteaRepository, error) {
	req, err := s.client.NewHubRequest(ctx, "GET", fmt.Sprintf("/gitea/simulators/%d/repo", simulatorID), nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var repo models.GiteaRepository
	if err := json.NewDecoder(resp.Body).Decode(&repo); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &repo, nil
}

// CreateSimulatorRepository creates a repository for a simulator
func (s *GiteaService) CreateSimulatorRepository(ctx context.Context, simulatorID int) (*models.GiteaRepository, error) {
	req, err := s.client.NewHubRequest(ctx, "POST", fmt.Sprintf("/gitea/simulators/%d/repo", simulatorID), nil)
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
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var repo models.GiteaRepository
	if err := json.NewDecoder(resp.Body).Decode(&repo); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &repo, nil
}
