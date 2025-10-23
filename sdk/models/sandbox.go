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
