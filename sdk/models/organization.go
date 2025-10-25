// Package models provides data structures for organization-related operations.
//
// This file defines models for Plato organizations, organization members, session
// summaries, and job metrics. These models are used when querying organization
// information, monitoring running sessions, and analyzing job performance metrics.
package models

type Organization struct {
	ID     int    `json:"id"`
	Name   string `json:"name"`
	APIKey string `json:"api_key"`
}

type OrganizationMember struct {
	ID    int    `json:"id"`
	Email string `json:"email"`
	Name  string `json:"name"`
	Role  string `json:"role"`
}

type SessionSummary struct {
	OrganizationID   int `json:"organization_id"`
	LastNHours       int `json:"last_n_hours"`
	RunningSessions  int `json:"running_sessions"`
	PendingSessions  int `json:"pending_sessions"`
	PeakRunningCount int `json:"peak_running_count"`
}

type RunningJobsResponse struct {
	OrganizationID int `json:"organization_id"`
	RunningJobs    int `json:"running_jobs"`
}

type JobMetrics struct {
	OrganizationID    int      `json:"organization_id"`
	P50TimeToStart    *float64 `json:"p50_time_to_start"`
	P90TimeToStart    *float64 `json:"p90_time_to_start"`
	P99TimeToStart    *float64 `json:"p99_time_to_start"`
	TotalJobsAnalyzed int      `json:"total_jobs_analyzed"`
	TimeWindowHours   float64  `json:"time_window_hours"`
}
