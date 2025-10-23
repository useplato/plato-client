package plato

import "fmt"

// APIError represents an error from the Plato API
type APIError struct {
	StatusCode int
	Message    string
	RequestID  string
}

func (e *APIError) Error() string {
	if e.RequestID != "" {
		return fmt.Sprintf("plato api error (status %d, request_id: %s): %s", e.StatusCode, e.RequestID, e.Message)
	}
	return fmt.Sprintf("plato api error (status %d): %s", e.StatusCode, e.Message)
}

// NetworkError represents a network-level error
type NetworkError struct {
	Err error
}

func (e *NetworkError) Error() string {
	return fmt.Sprintf("network error: %v", e.Err)
}

func (e *NetworkError) Unwrap() error {
	return e.Err
}

// ValidationError represents a client-side validation error
type ValidationError struct {
	Field   string
	Message string
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("validation error on field '%s': %s", e.Field, e.Message)
}

// RateLimitError represents a rate limiting error
type RateLimitError struct {
	RetryAfter int // seconds until retry is allowed
}

func (e *RateLimitError) Error() string {
	return fmt.Sprintf("rate limit exceeded, retry after %d seconds", e.RetryAfter)
}
