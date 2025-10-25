// Package services provides the organization service for Plato API operations.
//
// This file implements the OrganizationService which handles organization-level
// operations including querying running sessions, monitoring active jobs, and
// retrieving job performance metrics (p50, p90, p99 time-to-start). These
// operations help organizations monitor their resource usage and job performance.
package services

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"plato-sdk/models"
)

type OrganizationService struct {
	client ClientInterface
}

func NewOrganizationService(client ClientInterface) *OrganizationService {
	return &OrganizationService{
		client: client,
	}
}

// GetRunningSessions retrieves session information for the organization
// lastNHours: Number of hours to look back for peak calculation (default: 1)
func (s *OrganizationService) GetRunningSessions(ctx context.Context, lastNHours int) (*models.SessionSummary, error) {
	path := fmt.Sprintf("/user/organization/running-sessions?last_n_hours=%d", lastNHours)
	req, err := s.client.NewRequest(ctx, "GET", path, nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("got unexpected status code from %s: %d", path, resp.StatusCode)
	}

	var summary models.SessionSummary
	if err := json.NewDecoder(resp.Body).Decode(&summary); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &summary, nil
}

// GetRunningJobs retrieves the count of currently running jobs
func (s *OrganizationService) GetRunningJobs(ctx context.Context) (*models.RunningJobsResponse, error) {
	req, err := s.client.NewRequest(ctx, "GET", "/user/organization/running-jobs", nil)
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

	var jobsResp models.RunningJobsResponse
	if err := json.NewDecoder(resp.Body).Decode(&jobsResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &jobsResp, nil
}

// GetJobMetrics retrieves job performance metrics (p50, p90, p99 time-to-start)
// hours: Time window in hours (default: 24, accepts fractional hours)
func (s *OrganizationService) GetJobMetrics(ctx context.Context, hours float64) (*models.JobMetrics, error) {
	path := fmt.Sprintf("/user/organization/job-metrics?hours=%f", hours)
	req, err := s.client.NewRequest(ctx, "GET", path, nil)
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

	var metrics models.JobMetrics
	if err := json.NewDecoder(resp.Body).Decode(&metrics); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &metrics, nil
}
