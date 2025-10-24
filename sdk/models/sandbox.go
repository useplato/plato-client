package models

type Sandbox struct {
	// Job for this specific VM
	JobID string

	// Public ID for the VM
	PublicID string

	// Job group ID for accessing the VM
	JobGroupID string

	// URL for accessing the VM
	URL string

	// Status of the VM
	Status string

	// Correlation ID for monitoring SSE events
	CorrelationID string
}

// CreateSnapshotRequest represents a request to create a VM snapshot
type CreateSnapshotRequest struct {
	Service string  `json:"service,omitempty"`
	GitHash *string `json:"git_hash,omitempty"`
	Dataset *string `json:"dataset,omitempty"`
}
