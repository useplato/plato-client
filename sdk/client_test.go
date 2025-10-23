package plato

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestNewClient(t *testing.T) {
	apiKey := "test-api-key"
	client := NewClient(apiKey)

	if client.apiKey != apiKey {
		t.Errorf("expected apiKey %s, got %s", apiKey, client.apiKey)
	}

	if client.baseURL != "https://plato.so/api" {
		t.Errorf("expected baseURL https://plato.so/api, got %s", client.baseURL)
	}

	if client.timeout != 30*time.Second {
		t.Errorf("expected timeout 30s, got %v", client.timeout)
	}

	if client.httpClient == nil {
		t.Error("expected httpClient to be initialized")
	}

	if client.headers == nil {
		t.Error("expected headers map to be initialized")
	}

	if client.featureFlags == nil {
		t.Error("expected featureFlags map to be initialized")
	}

	if client.retryConfig == nil {
		t.Error("expected retryConfig to be initialized")
	}
}

func TestClientOptions(t *testing.T) {
	apiKey := "test-api-key"
	customURL := "https://custom.api.com"
	customTimeout := 60 * time.Second

	client := NewClient(apiKey,
		WithBaseURL(customURL),
		WithTimeout(customTimeout),
		WithHeader("X-Custom-Header", "value"),
		WithFeatureFlag("test-feature", true),
	)

	if client.baseURL != customURL {
		t.Errorf("expected baseURL %s, got %s", customURL, client.baseURL)
	}

	if client.timeout != customTimeout {
		t.Errorf("expected timeout %v, got %v", customTimeout, client.timeout)
	}

	if val, ok := client.headers["X-Custom-Header"]; !ok || val != "value" {
		t.Errorf("expected header X-Custom-Header with value 'value', got %v, %v", val, ok)
	}

	if !client.IsFeatureEnabled("test-feature") {
		t.Error("expected test-feature to be enabled")
	}
}

func TestWithHeaders(t *testing.T) {
	headers := map[string]string{
		"X-Header-1": "value1",
		"X-Header-2": "value2",
	}

	client := NewClient("test-key", WithHeaders(headers))

	for k, v := range headers {
		if val, ok := client.headers[k]; !ok || val != v {
			t.Errorf("expected header %s with value %s, got %v, %v", k, v, val, ok)
		}
	}
}

func TestWithFeatureFlags(t *testing.T) {
	flags := map[string]interface{}{
		"bool-flag":   true,
		"string-flag": "test",
		"int-flag":    42,
	}

	client := NewClient("test-key", WithFeatureFlags(flags))

	for k, expected := range flags {
		if val, ok := client.featureFlags[k]; !ok || val != expected {
			t.Errorf("expected flag %s with value %v, got %v, %v", k, expected, val, ok)
		}
	}
}

func TestGetFeatureFlag(t *testing.T) {
	client := NewClient("test-key",
		WithFeatureFlag("exists", "value"),
	)

	val, ok := client.GetFeatureFlag("exists")
	if !ok || val != "value" {
		t.Errorf("expected flag 'exists' with value 'value', got %v, %v", val, ok)
	}

	val, ok = client.GetFeatureFlag("does-not-exist")
	if ok {
		t.Errorf("expected flag 'does-not-exist' to not exist, got %v", val)
	}
}

func TestIsFeatureEnabled(t *testing.T) {
	tests := []struct {
		name     string
		flags    map[string]interface{}
		key      string
		expected bool
	}{
		{
			name:     "enabled boolean flag",
			flags:    map[string]interface{}{"feature": true},
			key:      "feature",
			expected: true,
		},
		{
			name:     "disabled boolean flag",
			flags:    map[string]interface{}{"feature": false},
			key:      "feature",
			expected: false,
		},
		{
			name:     "non-existent flag",
			flags:    map[string]interface{}{},
			key:      "feature",
			expected: false,
		},
		{
			name:     "non-boolean flag",
			flags:    map[string]interface{}{"feature": "string"},
			key:      "feature",
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			client := NewClient("test-key", WithFeatureFlags(tt.flags))
			result := client.IsFeatureEnabled(tt.key)
			if result != tt.expected {
				t.Errorf("expected IsFeatureEnabled to return %v, got %v", tt.expected, result)
			}
		})
	}
}

func TestNewRequest(t *testing.T) {
	apiKey := "test-api-key"
	client := NewClient(apiKey,
		WithHeader("X-Custom-Header", "custom-value"),
	)

	ctx := context.Background()
	req, err := client.NewRequest(ctx, "GET", "/test", nil)

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if req.Method != "GET" {
		t.Errorf("expected method GET, got %s", req.Method)
	}

	expectedURL := "https://plato.so/api/test"
	if req.URL.String() != expectedURL {
		t.Errorf("expected URL %s, got %s", expectedURL, req.URL.String())
	}

	// Check auth header
	authHeader := req.Header.Get("X-API-Key")
	expectedAuth := apiKey
	if authHeader != expectedAuth {
		t.Errorf("expected X-API-Key header %s, got %s", expectedAuth, authHeader)
	}

	// Check default headers
	if req.Header.Get("Content-Type") != "application/json" {
		t.Errorf("expected Content-Type application/json, got %s", req.Header.Get("Content-Type"))
	}

	if req.Header.Get("Accept") != "application/json" {
		t.Errorf("expected Accept application/json, got %s", req.Header.Get("Accept"))
	}

	// Check custom header
	if req.Header.Get("X-Custom-Header") != "custom-value" {
		t.Errorf("expected X-Custom-Header custom-value, got %s", req.Header.Get("X-Custom-Header"))
	}
}

func TestDo_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"success": true}`))
	}))
	defer server.Close()

	client := NewClient("test-key",
		WithBaseURL(server.URL),
		WithRetryConfig(&RetryConfig{MaxRetries: 0, RetryDelay: 0}),
	)

	req, _ := client.NewRequest(context.Background(), "GET", "/test", nil)
	resp, err := client.Do(req)

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}
}

func TestDo_RetryOn5xx(t *testing.T) {
	attempts := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts < 3 {
			w.WriteHeader(http.StatusInternalServerError)
		} else {
			w.WriteHeader(http.StatusOK)
		}
	}))
	defer server.Close()

	client := NewClient("test-key",
		WithBaseURL(server.URL),
		WithRetryConfig(&RetryConfig{MaxRetries: 3, RetryDelay: 1 * time.Millisecond}),
	)

	req, _ := client.NewRequest(context.Background(), "GET", "/test", nil)
	resp, err := client.Do(req)

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200 after retries, got %d", resp.StatusCode)
	}

	if attempts != 3 {
		t.Errorf("expected 3 attempts, got %d", attempts)
	}
}

func TestDo_NoRetryOn4xx(t *testing.T) {
	attempts := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		w.WriteHeader(http.StatusBadRequest)
	}))
	defer server.Close()

	client := NewClient("test-key",
		WithBaseURL(server.URL),
		WithRetryConfig(&RetryConfig{MaxRetries: 3, RetryDelay: 1 * time.Millisecond}),
	)

	req, _ := client.NewRequest(context.Background(), "GET", "/test", nil)
	resp, err := client.Do(req)

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", resp.StatusCode)
	}

	if attempts != 1 {
		t.Errorf("expected 1 attempt (no retry on 4xx), got %d", attempts)
	}
}

func TestWithRetryConfig(t *testing.T) {
	customRetry := &RetryConfig{
		MaxRetries: 5,
		RetryDelay: 2 * time.Second,
	}

	client := NewClient("test-key", WithRetryConfig(customRetry))

	if client.retryConfig.MaxRetries != 5 {
		t.Errorf("expected MaxRetries 5, got %d", client.retryConfig.MaxRetries)
	}

	if client.retryConfig.RetryDelay != 2*time.Second {
		t.Errorf("expected RetryDelay 2s, got %v", client.retryConfig.RetryDelay)
	}
}

func TestWithHTTPClient(t *testing.T) {
	customClient := &http.Client{
		Timeout: 5 * time.Second,
	}

	client := NewClient("test-key", WithHTTPClient(customClient))

	if client.httpClient != customClient {
		t.Error("expected custom HTTP client to be used")
	}
}
