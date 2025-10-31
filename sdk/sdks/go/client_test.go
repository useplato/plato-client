package plato_test

import (
	"context"
	"net/http"
	"testing"
	"time"

	option "sdk/option"

	plato "github.com/plato-app/plato-go-sdk"
)

// Example demonstrating MonitorOperationSync usage
func ExampleClient_MonitorOperationSync() {
	// Create client
	c := plato.NewClient(
		option.WithBaseURL("https://api.plato.so"),
		option.WithHTTPHeader(http.Header{
			"X-API-Key": {"your-api-key"},
		}),
	)

	// Monitor operation with 10 minute timeout
	ctx := context.Background()
	err := c.MonitorOperationSync(ctx, "correlation-id-123", 10*time.Minute)
	if err != nil {
		// Handle error
		return
	}

	// Operation completed successfully
}

// Example demonstrating MonitorOperationWithEvents usage
func ExampleClient_MonitorOperationWithEvents() {
	// Create client
	c := plato.NewClient(
		option.WithBaseURL("https://api.plato.so"),
		option.WithHTTPHeader(http.Header{
			"X-API-Key": {"your-api-key"},
		}),
	)

	// Create channel for receiving events
	eventChan := make(chan string, 10)

	// Start goroutine to print events
	go func() {
		for msg := range eventChan {
			// Process event messages
			_ = msg
		}
	}()

	// Monitor operation with real-time events
	ctx := context.Background()
	err := c.MonitorOperationWithEvents(ctx, "correlation-id-123", 10*time.Minute, eventChan)
	close(eventChan)

	if err != nil {
		// Handle error
		return
	}

	// Operation completed successfully
}

// TestMonitorHelpersMethods verifies that the helper methods exist and have correct signatures
func TestMonitorHelpersMethods(t *testing.T) {
	c := plato.NewClient(
		option.WithBaseURL("https://api.plato.so"),
	)

	// Verify MonitorOperationSync exists and has correct signature
	t.Run("MonitorOperationSync exists", func(t *testing.T) {
		ctx := context.Background()
		err := c.MonitorOperationSync(ctx, "test-id", 1*time.Second)
		// We expect an error since we're not hitting a real endpoint
		if err == nil {
			t.Log("Expected error due to invalid endpoint, but method signature is correct")
		}
	})

	// Verify MonitorOperationWithEvents exists and has correct signature
	t.Run("MonitorOperationWithEvents exists", func(t *testing.T) {
		ctx := context.Background()
		eventChan := make(chan string, 10)
		err := c.MonitorOperationWithEvents(ctx, "test-id", 1*time.Second, eventChan)
		close(eventChan)
		// We expect an error since we're not hitting a real endpoint
		if err == nil {
			t.Log("Expected error due to invalid endpoint, but method signature is correct")
		}
	})
}

// TestClientWrapsGeneratedClient verifies the client properly wraps the generated client
func TestClientWrapsGeneratedClient(t *testing.T) {
	c := plato.NewClient()

	// Verify we can access generated client methods through embedding
	if c.Client == nil {
		t.Error("Client should embed generated client")
	}

	// Test that we can call generated client methods
	ctx := context.Background()
	_, err := c.GetRunningSessionsCount(ctx)
	// We expect an error since we're not authenticated, but the method should exist
	if err == nil {
		t.Log("Method exists and is accessible through wrapper")
	}
}
