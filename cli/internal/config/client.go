// Package config provides configuration management for the Plato CLI.
//
// This file handles loading configuration from environment variables and .env files,
// and creating configured Plato SDK clients.
package config

import (
	"os"

	plato "plato-sdk"

	"github.com/joho/godotenv"
)

// LoadClient loads configuration from environment and creates a Plato client
func LoadClient() *plato.PlatoClient {
	// Load .env file
	godotenv.Load()

	apiKey := os.Getenv("PLATO_API_KEY")
	baseURL := os.Getenv("PLATO_BASE_URL")
	hubBaseURL := os.Getenv("PLATO_HUB_API_URL")

	var opts []plato.ClientOption
	if baseURL != "" {
		opts = append(opts, plato.WithBaseURL(baseURL))
	}

	// Hub API URL defaults to https://plato.so/api if not explicitly set
	if hubBaseURL == "" {
		hubBaseURL = "https://plato.so/api"
	}
	opts = append(opts, plato.WithHubBaseURL(hubBaseURL))

	return plato.NewClient(apiKey, opts...)
}

// GetAPIKey returns the API key from environment
func GetAPIKey() string {
	godotenv.Load()
	return os.Getenv("PLATO_API_KEY")
}

// GetBaseURL returns the base URL from environment or default
func GetBaseURL() string {
	godotenv.Load()
	baseURL := os.Getenv("PLATO_BASE_URL")
	if baseURL == "" {
		return "https://plato.so/api"
	}
	return baseURL
}
