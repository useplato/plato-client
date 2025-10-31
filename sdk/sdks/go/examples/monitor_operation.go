package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"time"

	plato "github.com/plato-app/plato-go-sdk"
	sdk "sdk"
	option "sdk/option"
)

func main() {
	// Create client with API key in header
	client := plato.NewClient(
		option.WithBaseURL("https://api.plato.so"),
		option.WithHTTPHeader(http.Header{
			"X-API-Key": {"your-api-key"},
		}),
	)

	ctx := context.Background()

	// Example 1: Create a sandbox and monitor its creation
	fmt.Println("Example 1: Creating sandbox and monitoring with sync method")
	if err := createAndMonitorSync(ctx, client); err != nil {
		log.Printf("Example 1 failed: %v\n", err)
	}

	// Example 2: Monitor with real-time events
	fmt.Println("\nExample 2: Creating sandbox and monitoring with events")
	if err := createAndMonitorWithEvents(ctx, client); err != nil {
		log.Printf("Example 2 failed: %v\n", err)
	}

	// Example 3: Low-level stream access
	fmt.Println("\nExample 3: Low-level stream monitoring")
	if err := monitorWithLowLevelStream(ctx, client, "correlation-id-123"); err != nil {
		log.Printf("Example 3 failed: %v\n", err)
	}
}

func createAndMonitorSync(ctx context.Context, client *plato.Client) error {
	// Create a sandbox
	req := &sdk.CreateSandboxRequest{
		Dataset: "base",
		Alias:   stringPtr("my-sandbox"),
	}

	fmt.Println("Creating sandbox...")
	sandbox, err := client.CreateSandbox(ctx, req)
	if err != nil {
		return fmt.Errorf("failed to create sandbox: %w", err)
	}

	fmt.Printf("Sandbox created with correlation ID: %s\n", *sandbox.CorrelationId)

	// Monitor the creation operation synchronously
	fmt.Println("Monitoring operation...")
	err = client.MonitorOperationSync(ctx, *sandbox.CorrelationId, 10*time.Minute)
	if err != nil {
		return fmt.Errorf("operation failed: %w", err)
	}

	fmt.Println("✓ Operation completed successfully!")
	return nil
}

func createAndMonitorWithEvents(ctx context.Context, client *plato.Client) error {
	// Create a sandbox
	req := &sdk.CreateSandboxRequest{
		Dataset: "base",
		Alias:   stringPtr("my-sandbox-2"),
	}

	fmt.Println("Creating sandbox...")
	sandbox, err := client.CreateSandbox(ctx, req)
	if err != nil {
		return fmt.Errorf("failed to create sandbox: %w", err)
	}

	fmt.Printf("Sandbox created with correlation ID: %s\n", *sandbox.CorrelationId)

	// Create channel for receiving events
	eventChan := make(chan string, 10)

	// Start goroutine to print events as they arrive
	go func() {
		for msg := range eventChan {
			fmt.Printf("  📡 %s\n", msg)
		}
	}()

	// Monitor the operation with real-time events
	fmt.Println("Monitoring operation with events...")
	err = client.MonitorOperationWithEvents(ctx, *sandbox.CorrelationId, 10*time.Minute, eventChan)
	close(eventChan)

	if err != nil {
		return fmt.Errorf("operation failed: %w", err)
	}

	fmt.Println("✓ Operation completed successfully!")
	return nil
}

func monitorWithLowLevelStream(ctx context.Context, client *plato.Client, correlationID string) error {
	fmt.Printf("Monitoring correlation ID: %s\n", correlationID)

	// Get the SSE stream
	stream, err := client.MonitorOperation(ctx, correlationID)
	if err != nil {
		return fmt.Errorf("failed to create SSE stream: %w", err)
	}
	defer stream.Close()

	// Read events from stream
	for {
		event, err := stream.Recv()
		if err != nil {
			return fmt.Errorf("stream error: %w", err)
		}

		// Handle different event types
		switch event.Type {
		case sdk.OperationEventTypeConnected:
			fmt.Println("  🔌 Connected to SSE stream")
			continue

		case sdk.OperationEventTypeProgress:
			if event.Message != nil {
				fmt.Printf("  ⏳ Progress: %s\n", *event.Message)
			}
			continue

		case sdk.OperationEventTypeRunResult, sdk.OperationEventTypeSshResult:
			if event.Success != nil && *event.Success {
				fmt.Println("  ✓ Operation completed successfully!")
				return nil
			}
			errorMsg := "Operation failed"
			if event.Error != nil {
				errorMsg = *event.Error
			} else if event.Message != nil {
				errorMsg = *event.Message
			}
			return fmt.Errorf("operation failed: %s", errorMsg)

		case sdk.OperationEventTypeError:
			errorMsg := "Unknown error"
			if event.Error != nil {
				errorMsg = *event.Error
			} else if event.Message != nil {
				errorMsg = *event.Message
			}
			return fmt.Errorf("error event: %s", errorMsg)

		default:
			fmt.Printf("  ℹ️  Unknown event type: %s\n", event.Type)
		}
	}
}

func stringPtr(s string) *string {
	return &s
}

