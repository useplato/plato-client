# Plato Go SDK

A Go SDK wrapper for the Plato API that provides additional helper methods on top of the auto-generated Fern SDK. This package ensures that custom functionality persists even when the underlying generated SDK is regenerated.

## Features

- **SSE Monitoring Helpers**: Convenient methods for monitoring long-running operations
- **Future-Proof**: Wraps the generated SDK so custom code isn't lost during regeneration
- **Full API Access**: All methods from the generated SDK are available through composition

## Installation

```bash
go get github.com/plato-app/plato-go-sdk
```

## Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    plato "github.com/plato-app/plato-go-sdk"
    option "sdk/option"
)

func main() {
    // Create client
    client := plato.NewClient(
        option.WithBaseURL("https://api.plato.so"),
        option.WithHTTPHeader(map[string][]string{
            "X-API-Key": {"your-api-key"},
        }),
    )

    // Monitor a long-running operation
    ctx := context.Background()
    err := client.MonitorOperationSync(ctx, "correlation-id-123", 10*time.Minute)
    if err != nil {
        log.Fatalf("Operation failed: %v", err)
    }

    fmt.Println("Operation completed successfully!")
}
```

## SSE Monitoring Helper Methods

The SDK provides convenient helper methods for monitoring long-running operations via Server-Sent Events (SSE).

### MonitorOperationSync

Monitor an operation synchronously and wait for completion:

```go
import (
    "context"
    "time"
    plato "github.com/plato-app/plato-go-sdk"
    option "sdk/option"
)

func monitorOperation() error {
    client := plato.NewClient(
        option.WithBaseURL("https://api.plato.so"),
        option.WithHTTPHeader(map[string][]string{
            "X-API-Key": {"your-api-key"},
        }),
    )

    // Monitor operation with 10 minute timeout
    ctx := context.Background()
    err := client.MonitorOperationSync(ctx, "correlation-id-123", 10*time.Minute)
    if err != nil {
        return fmt.Errorf("operation failed: %w", err)
    }

    fmt.Println("Operation completed successfully!")
    return nil
}
```

### MonitorOperationWithEvents

Monitor an operation with real-time event updates:

```go
func monitorWithEvents() error {
    client := plato.NewClient(
        option.WithBaseURL("https://api.plato.so"),
        option.WithHTTPHeader(map[string][]string{
            "X-API-Key": {"your-api-key"},
        }),
    )

    // Create channel for receiving events
    eventChan := make(chan string, 10)

    // Start goroutine to print events as they arrive
    go func() {
        for msg := range eventChan {
            fmt.Println("Event:", msg)
        }
    }()

    // Monitor operation with real-time events
    ctx := context.Background()
    err := client.MonitorOperationWithEvents(ctx, "correlation-id-123", 10*time.Minute, eventChan)
    close(eventChan)

    if err != nil {
        return fmt.Errorf("operation failed: %w", err)
    }

    return nil
}
```

## Using Generated SDK Methods

All methods from the auto-generated Fern SDK are available through the wrapper:

```go
client := plato.NewClient(
    option.WithHTTPHeader(map[string][]string{
        "X-API-Key": {"your-api-key"},
    }),
)

// Call any generated SDK method directly
response, err := client.MakeEnvironment(ctx, &sdk.MakeEnvironmentRequest{
    InterfaceType: "interface_type",
    EnvId: "env_id",
})

// Get job status
status, err := client.GetJobStatus(ctx, "job-id")

// List simulators
simulators, err := client.ListSimulators(ctx)
```

## Advanced Usage

### Low-level Stream Access

If you need more control over SSE event handling, use the low-level `MonitorOperation` method:

```go
stream, err := client.MonitorOperation(ctx, correlationID)
if err != nil {
    return err
}
defer stream.Close()

for {
    event, err := stream.Recv()
    if err == io.EOF {
        break
    }
    if err != nil {
        return err
    }

    // Handle event based on type
    switch event.Type {
    case sdk.OperationEventTypeConnected:
        // Connection established
    case sdk.OperationEventTypeProgress:
        // Progress update
        fmt.Println("Progress:", *event.Message)
    case sdk.OperationEventTypeRunResult, sdk.OperationEventTypeSshResult:
        // Operation completed
        if event.Success != nil && *event.Success {
            return nil
        }
    case sdk.OperationEventTypeError:
        // Error occurred
        return fmt.Errorf("operation error: %s", *event.Error)
    }
}
```

### Request Options

Configure the client or individual requests with various options:

```go
// Configure client defaults
client := plato.NewClient(
    option.WithHTTPHeader(map[string][]string{
        "X-API-Key": {"your-api-key"},
    }),
    option.WithBaseURL("https://api.plato.so"),
    option.WithHTTPClient(&http.Client{
        Timeout: 30 * time.Second,
    }),
)

// Override options for specific requests
response, err := client.MakeEnvironment(
    ctx,
    request,
    option.WithMaxAttempts(3),
)
```

## Architecture

This SDK wraps the auto-generated Fern SDK (`sdk/sdks/go-generated`) through composition:

```
sdk/sdks/go/           # This package (custom helpers that persist)
└── imports
    sdk/sdks/go-generated/  # Auto-generated by Fern (can be regenerated)
```

When Fern regenerates the SDK, your custom helper methods in `sdk/sdks/go/` remain intact.

## Error Handling

The SDK provides structured error types:

```go
response, err := client.MakeEnvironment(ctx, request)
if err != nil {
    var apiError *core.APIError
    if errors.As(err, &apiError) {
        fmt.Printf("API Error: %d - %s\n", apiError.StatusCode, apiError.Message)
    }
    return err
}
```

## Contributing

Contributions are welcome! Since this package wraps the generated SDK, you can safely add new helper methods here without worrying about regeneration.

## License

See the main repository LICENSE file.

## Documentation

For full API documentation of the underlying generated SDK, see:
- [Generated SDK Reference](../go-generated/reference.md)
- [Generated SDK README](../go-generated/README.md)

