package services

import (
	"context"
	"encoding/json"
	"fmt"
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
