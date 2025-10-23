package services

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"plato-sdk/models"
)

type SimulatorService struct {
	client ClientInterface
}

func NewSimulatorService(client ClientInterface) *SimulatorService {
	return &SimulatorService{
		client: client,
	}
}

// List retrieves all available simulators
func (s *SimulatorService) List(ctx context.Context) ([]*models.SimulatorListItem, error) {
	req, err := s.client.NewRequest(ctx, "GET", "/simulator/list", nil)
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

	var simulators []*models.SimulatorListItem
	if err := json.NewDecoder(resp.Body).Decode(&simulators); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return simulators, nil
}

// GetVersions retrieves all versions for a specific simulator
func (s *SimulatorService) GetVersions(ctx context.Context, simulatorName string) ([]*models.SimulatorVersion, error) {
	req, err := s.client.NewRequest(ctx, "GET", fmt.Sprintf("/simulator/%s/versions", simulatorName), nil)
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

	// Read the response body for logging
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	// Response might be wrapped in an object with a "versions" key
	var response struct {
		Versions []*models.SimulatorVersion `json:"versions"`
	}
	if err := json.Unmarshal(bodyBytes, &response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return response.Versions, nil
}
