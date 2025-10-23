package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/joho/godotenv"
	plato "plato-sdk"
)

func main() {
	// Load environment variables from .env file
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using environment variables")
	}

	// Get API key from environment
	apiKey := os.Getenv("PLATO_API_KEY")
	if apiKey == "" {
		log.Fatal("PLATO_API_KEY environment variable is required")
	}

	baseURL := os.Getenv("PLATO_BASE_URL")
	if baseURL == "" {
		baseURL = "https://plato.so/api"
	}

	// Create a new Plato client with your API key
	// The API key automatically gives you access to your organization
	client := plato.NewClient(
		apiKey,
		plato.WithBaseURL(baseURL),
	)

	ctx := context.Background()

	// Get running sessions for the past hour
	sessions, err := client.Organization.GetRunningSessions(ctx, 1)
	if err != nil {
		log.Fatalf("Failed to get running sessions: %v", err)
	}

	fmt.Printf("Organization ID: %d\n", sessions.OrganizationID)
	fmt.Printf("Running sessions: %d\n", sessions.RunningSessions)
	fmt.Printf("Pending sessions: %d\n", sessions.PendingSessions)
	fmt.Printf("Peak running count (last %d hours): %d\n\n", sessions.LastNHours, sessions.PeakRunningCount)

	// Get running jobs count
	jobs, err := client.Organization.GetRunningJobs(ctx)
	if err != nil {
		log.Fatalf("Failed to get running jobs: %v", err)
	}

	fmt.Printf("Running jobs: %d\n\n", jobs.RunningJobs)

	// Get job metrics for the past 24 hours
	metrics, err := client.Organization.GetJobMetrics(ctx, 24.0)
	if err != nil {
		log.Fatalf("Failed to get job metrics: %v", err)
	}

	fmt.Printf("Job Metrics (last %.1f hours):\n", metrics.TimeWindowHours)
	fmt.Printf("  Total jobs analyzed: %d\n", metrics.TotalJobsAnalyzed)
	if metrics.P50TimeToStart != nil {
		fmt.Printf("  P50 time to start: %.2f seconds\n", *metrics.P50TimeToStart)
	}
	if metrics.P90TimeToStart != nil {
		fmt.Printf("  P90 time to start: %.2f seconds\n", *metrics.P90TimeToStart)
	}
	if metrics.P99TimeToStart != nil {
		fmt.Printf("  P99 time to start: %.2f seconds\n", *metrics.P99TimeToStart)
	}
}
