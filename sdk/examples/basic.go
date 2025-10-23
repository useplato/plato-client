package main

import (
	"fmt"
	"time"

	plato "plato-sdk"
)

func main() {
	// Create a client with custom options
	client := plato.NewClient(
		"your-api-key",
		plato.WithBaseURL("https://api.plato.so"),
		plato.WithTimeout(60*time.Second),
		plato.WithHeader("X-Custom-Header", "custom-value"),
		plato.WithFeatureFlag("new-feature", true),
		plato.WithRetryConfig(&plato.RetryConfig{
			MaxRetries: 5,
			RetryDelay: 2 * time.Second,
		}),
	)

	// Check feature flags
	if client.IsFeatureEnabled("new-feature") {
		fmt.Println("New feature is enabled!")
	}

	// Get a feature flag value
	if val, ok := client.GetFeatureFlag("new-feature"); ok {
		fmt.Printf("Feature flag value: %v\n", val)
	}

	fmt.Println("Client initialized successfully!")
}
