// Package plato provides the main client for interacting with the Plato API.
//
// This file contains the PlatoClient struct and associated configuration options
// for making authenticated HTTP requests to the Plato platform. The client provides
// access to all Plato services including Sandbox, Organization, Simulator, Environment,
// and Gitea operations.
//
// The client is thread-safe and immutable after creation, supporting concurrent usage
// across multiple goroutines. It includes built-in retry logic, timeout configuration,
// and custom header support.
package plato

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"plato-sdk/services"
)

// ClientOption is a function that configures a PlatoClient
type ClientOption func(*PlatoClient)

// PlatoClient is the main client for interacting with the Plato API
// After creation, the client is immutable and safe for concurrent use
type PlatoClient struct {
	baseURL    string
	hubBaseURL string // Separate base URL for Gitea/Hub operations
	apiKey     string
	httpClient *http.Client

	// Custom headers to include in all requests
	headers map[string]string

	// Feature flags cache
	featureFlags map[string]interface{}

	// Session configuration
	timeout     time.Duration
	retryConfig *RetryConfig

	// Service groups
	Sandbox      *services.SandboxService
	Organization *services.OrganizationService
	Simulator    *services.SimulatorService
	Environment  *services.EnvironmentService
	Gitea        *services.GiteaService
}

// RetryConfig configures retry behavior for failed requests
type RetryConfig struct {
	MaxRetries int
	RetryDelay time.Duration
}

// NewClient creates a new PlatoClient with the given options
func NewClient(apiKey string, opts ...ClientOption) *PlatoClient {
	// Allow empty API key - it will be checked at the CLI level with a friendly message
	// if apiKey == "" {
	// 	panic("PLATO_API_KEY is not set. Please set your API key in .env file or environment variables")
	// }

	client := &PlatoClient{
		baseURL:      "https://plato.so/api",
		hubBaseURL:   "https://plato.so/api", // Default hub to same as base
		apiKey:       apiKey,
		headers:      make(map[string]string),
		featureFlags: make(map[string]interface{}),
		timeout:      30 * time.Second,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		retryConfig: &RetryConfig{
			MaxRetries: 3,
			RetryDelay: time.Second,
		},
	}

	// Apply options
	for _, opt := range opts {
		opt(client)
	}

	// Initialize services
	client.Sandbox = services.NewSandboxService(client)
	client.Organization = services.NewOrganizationService(client)
	client.Simulator = services.NewSimulatorService(client)
	client.Environment = services.NewEnvironmentService(client)
	client.Gitea = services.NewGiteaService(client)

	return client
}

// WithBaseURL sets a custom base URL for the client
func WithBaseURL(url string) ClientOption {
	return func(c *PlatoClient) {
		c.baseURL = url
	}
}

// WithHubBaseURL sets a custom base URL for hub/gitea operations
func WithHubBaseURL(url string) ClientOption {
	return func(c *PlatoClient) {
		c.hubBaseURL = url
	}
}

// WithTimeout sets the HTTP client timeout
func WithTimeout(timeout time.Duration) ClientOption {
	return func(c *PlatoClient) {
		c.timeout = timeout
		c.httpClient.Timeout = timeout
	}
}

// WithRetryConfig sets the retry configuration
func WithRetryConfig(config *RetryConfig) ClientOption {
	return func(c *PlatoClient) {
		c.retryConfig = config
	}
}

// WithHTTPClient sets a custom HTTP client
func WithHTTPClient(httpClient *http.Client) ClientOption {
	return func(c *PlatoClient) {
		c.httpClient = httpClient
	}
}

// WithHeader adds a custom header that will be included in all requests
func WithHeader(key, value string) ClientOption {
	return func(c *PlatoClient) {
		c.headers[key] = value
	}
}

// WithHeaders adds multiple custom headers that will be included in all requests
func WithHeaders(headers map[string]string) ClientOption {
	return func(c *PlatoClient) {
		for k, v := range headers {
			c.headers[k] = v
		}
	}
}

// WithFeatureFlag sets a feature flag value
func WithFeatureFlag(key string, value interface{}) ClientOption {
	return func(c *PlatoClient) {
		c.featureFlags[key] = value
	}
}

// WithFeatureFlags sets multiple feature flags
func WithFeatureFlags(flags map[string]interface{}) ClientOption {
	return func(c *PlatoClient) {
		for k, v := range flags {
			c.featureFlags[k] = v
		}
	}
}

// GetFeatureFlag retrieves a feature flag value
func (c *PlatoClient) GetFeatureFlag(key string) (interface{}, bool) {
	val, ok := c.featureFlags[key]
	return val, ok
}

// IsFeatureEnabled checks if a boolean feature flag is enabled
func (c *PlatoClient) IsFeatureEnabled(key string) bool {
	val, ok := c.featureFlags[key]
	if !ok {
		return false
	}
	boolVal, ok := val.(bool)
	return ok && boolVal
}

// GetAPIKey returns the configured API key
func (c *PlatoClient) GetAPIKey() string {
	return c.apiKey
}

// GetBaseURL returns the configured base URL
func (c *PlatoClient) GetBaseURL() string {
	return c.baseURL
}

// GetHubBaseURL returns the configured hub base URL
func (c *PlatoClient) GetHubBaseURL() string {
	return c.hubBaseURL
}

// NewRequest creates a new HTTP request with auth headers and custom headers
func (c *PlatoClient) NewRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error) {
	url := fmt.Sprintf("%s%s", c.baseURL, path)

	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set auth header
	req.Header.Set("X-API-Key", c.apiKey)

	// Set default headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	// Set custom headers
	for key, value := range c.headers {
		req.Header.Set(key, value)
	}

	return req, nil
}

// NewHubRequest creates a new HTTP request for hub/gitea operations with auth headers and custom headers
func (c *PlatoClient) NewHubRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error) {
	url := fmt.Sprintf("%s%s", c.hubBaseURL, path)

	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set auth header
	req.Header.Set("X-API-Key", c.apiKey)

	// Set default headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	// Set custom headers
	for key, value := range c.headers {
		req.Header.Set(key, value)
	}

	return req, nil
}

// Do executes an HTTP request with retry logic
// logAPICall logs API calls to plato_error.log
func logAPICall(method, path string, statusCode int, err error) {
	f, fileErr := os.OpenFile("plato_error.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if fileErr != nil {
		return
	}
	defer f.Close()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	var logMsg string
	if err != nil {
		logMsg = fmt.Sprintf("[%s] API: %s %s - ERROR: %v\n", timestamp, method, path, err)
	} else if statusCode >= 400 {
		logMsg = fmt.Sprintf("[%s] API: %s %s - STATUS: %d\n", timestamp, method, path, statusCode)
	} else {
		logMsg = fmt.Sprintf("[%s] API: %s %s - STATUS: %d\n", timestamp, method, path, statusCode)
	}
	_, _ = f.WriteString(logMsg) // Ignore write errors for logging
}

func (c *PlatoClient) Do(req *http.Request) (*http.Response, error) {
	var resp *http.Response
	var err error

	for attempt := 0; attempt <= c.retryConfig.MaxRetries; attempt++ {
		resp, err = c.httpClient.Do(req)

		// Success or non-retryable error
		if err == nil && resp.StatusCode < 500 {
			// Log the API call
			logAPICall(req.Method, req.URL.Path, resp.StatusCode, nil)
			return resp, nil
		}

		// Don't retry on last attempt
		if attempt < c.retryConfig.MaxRetries {
			time.Sleep(c.retryConfig.RetryDelay * time.Duration(attempt+1))
		}
	}

	// Log failed API call
	if err != nil {
		logAPICall(req.Method, req.URL.Path, 0, err)
	} else if resp != nil {
		logAPICall(req.Method, req.URL.Path, resp.StatusCode, fmt.Errorf("request failed after retries"))
	}

	return resp, err
}
