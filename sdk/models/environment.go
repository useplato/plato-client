// Package models provides data structures for environment-related operations.
//
// This file defines models for Plato environments, job status, worker status,
// and reset operations. These models are used when creating, managing, and
// monitoring Plato environments and their associated jobs.
package models

// Environment represents a Plato environment
type Environment struct {
	JobID string
	EnvID string
	Alias string
}

// JobStatus represents the status of a job
type JobStatus struct {
	Status string `json:"status"`
}

// WorkerStatus represents the readiness status of a worker
type WorkerStatus struct {
	Ready  bool    `json:"ready"`
	Error  *string `json:"error"`
}

// ResetResponse represents the response from resetting an environment
type ResetResponse struct {
	Success bool `json:"success"`
	Error   *string `json:"error"`
	Data    struct {
		RunSessionID string `json:"run_session_id"`
	} `json:"data"`
}
