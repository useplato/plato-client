// Package plato provides a wrapper around the auto-generated Fern SDK
// with additional helper methods that won't be lost during regeneration.
package plato

import (
	"context"
	"fmt"
	"io"
	"time"

	sdk "sdk"
	client "sdk/client"
	option "sdk/option"
)

// Client wraps the generated Fern client with additional helper methods
type Client struct {
	*client.Client
}

// NewClient creates a new Plato client with the given options
func NewClient(opts ...option.RequestOption) *Client {
	return &Client{
		Client: client.NewClient(opts...),
	}
}

// MonitorOperationSync monitors an SSE stream for operation completion and returns when done.
// This is a synchronous wrapper around MonitorOperation that handles the stream internally.
//
// It returns:
//   - nil on successful completion (when event.Success == true)
//   - error on failure or timeout
//
// The function automatically handles:
//   - "connected" events: continues listening
//   - "error" events: returns error immediately
//   - "run_result", "ssh_result", or other completion events: checks Success field and returns accordingly
//
// Example usage:
//
//	err := client.MonitorOperationSync(ctx, correlationID, 10*time.Minute)
//	if err != nil {
//	    log.Fatalf("Operation failed: %v", err)
//	}
//	log.Println("Operation completed successfully")
func (c *Client) MonitorOperationSync(
	ctx context.Context,
	correlationID string,
	timeout time.Duration,
	opts ...option.RequestOption,
) error {
	// Set timeout on context
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	// Get the SSE stream
	stream, err := c.Client.MonitorOperation(ctx, correlationID, opts...)
	if err != nil {
		return fmt.Errorf("failed to create SSE stream: %w", err)
	}
	defer stream.Close()

	// Read events from stream
	for {
		event, err := stream.Recv()
		if err != nil {
			if err == io.EOF {
				return fmt.Errorf("SSE stream ended without completion")
			}
			return fmt.Errorf("error reading SSE stream: %w", err)
		}

		// Handle different event types
		switch event.Type {
		case sdk.OperationEventTypeConnected:
			// Initial connection, continue listening
			continue

		case sdk.OperationEventTypeError:
			// Error event
			errorMsg := ""
			if event.Error != nil {
				errorMsg = *event.Error
			} else if event.Message != nil {
				errorMsg = *event.Message
			}
			if errorMsg == "" {
				errorMsg = "Operation error"
			}
			return fmt.Errorf("operation error: %s", errorMsg)

		case sdk.OperationEventTypeProgress:
			// Progress event, continue listening
			continue

		default:
			// Handle completion events (run_result, ssh_result, or any other terminal event)
			// Check success field
			if event.Success != nil && *event.Success {
				return nil // Success!
			}

			// Operation failed
			errorMsg := ""
			if event.Error != nil {
				errorMsg = *event.Error
			} else if event.Message != nil {
				errorMsg = *event.Message
			}
			if errorMsg == "" {
				errorMsg = "Operation failed"
			}
			return fmt.Errorf("operation failed: %s", errorMsg)
		}
	}
}

// MonitorOperationWithEvents monitors an SSE stream and sends event details to a channel.
// This provides real-time progress updates as events are received.
//
// The eventChan receives:
//   - Debug messages (prefixed with [DEBUG])
//   - Progress messages from the event.Message field
//   - Event type indicators when no message is available
//
// The function returns:
//   - nil on successful completion (when event.Success == true)
//   - error on failure or timeout
//
// Example usage:
//
//	eventChan := make(chan string, 10)
//	go func() {
//	    for msg := range eventChan {
//	        fmt.Println(msg)
//	    }
//	}()
//
//	err := client.MonitorOperationWithEvents(ctx, correlationID, 10*time.Minute, eventChan)
//	close(eventChan)
//	if err != nil {
//	    log.Fatalf("Operation failed: %v", err)
//	}
func (c *Client) MonitorOperationWithEvents(
	ctx context.Context,
	correlationID string,
	timeout time.Duration,
	eventChan chan<- string,
	opts ...option.RequestOption,
) error {
	// Set timeout on context
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	// Get the SSE stream
	stream, err := c.Client.MonitorOperation(ctx, correlationID, opts...)
	if err != nil {
		return fmt.Errorf("failed to create SSE stream: %w", err)
	}
	defer stream.Close()

	// Read events from stream
	for {
		event, err := stream.Recv()
		if err != nil {
			if err == io.EOF {
				eventChan <- "[DEBUG] SSE stream ended without receiving completion event"
				return fmt.Errorf("SSE stream ended without completion")
			}
			eventChan <- fmt.Sprintf("[DEBUG] Stream error: %v", err)
			return fmt.Errorf("error reading SSE stream: %w", err)
		}

		// Send debug info about the received event
		successStr := "nil"
		if event.Success != nil {
			successStr = fmt.Sprintf("%v", *event.Success)
		}
		messageStr := ""
		if event.Message != nil {
			messageStr = *event.Message
		}
		eventChan <- fmt.Sprintf("[DEBUG] Received event - Type: %s, Success: %s, Message: %s",
			event.Type, successStr, messageStr)

		// Send event message to channel if available
		if event.Message != nil && *event.Message != "" {
			eventChan <- *event.Message
		} else if event.Type != sdk.OperationEventTypeConnected {
			// If no message but we have a type, send that
			eventChan <- fmt.Sprintf("[%s]", event.Type)
		}

		// Handle different event types
		switch event.Type {
		case sdk.OperationEventTypeConnected:
			// Initial connection, continue listening
			eventChan <- "[DEBUG] SSE connected"
			continue

		case sdk.OperationEventTypeError:
			// Error event
			errorMsg := ""
			if event.Error != nil {
				errorMsg = *event.Error
			} else if event.Message != nil {
				errorMsg = *event.Message
			}
			if errorMsg == "" {
				errorMsg = "Operation error"
			}
			eventChan <- fmt.Sprintf("[DEBUG] Error event: %s", errorMsg)
			return fmt.Errorf("operation error: %s", errorMsg)

		case sdk.OperationEventTypeProgress:
			// Progress event, continue listening
			continue

		default:
			// Handle completion events (run_result, ssh_result, or any other terminal event)
			eventChan <- fmt.Sprintf("[DEBUG] Event type=%s, success=%s", event.Type, successStr)

			// Check success field
			if event.Success != nil && *event.Success {
				return nil // Success!
			}

			// Operation failed
			errorMsg := ""
			if event.Error != nil {
				errorMsg = *event.Error
			} else if event.Message != nil {
				errorMsg = *event.Message
			}
			if errorMsg == "" {
				errorMsg = "Operation failed"
			}
			return fmt.Errorf("operation failed: %s", errorMsg)
		}
	}
}
