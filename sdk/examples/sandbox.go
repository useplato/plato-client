package main

import (
	"context"
	"fmt"
	"log"

	plato "plato-sdk"
	"plato-sdk/models"
)

func main() {
	// Create a new Plato client
	client := plato.NewClient(
		"your-api-key",
		plato.WithBaseURL("https://api.plato.so"),
	)

	ctx := context.Background()

	// Create a new sandbox using the client's Sandbox service
	config := models.VMConfiguration{
		CPUCount:  2,
		Memory:    4096,  // 4GB
		DiskSpace: 20480, // 20GB
	}

	sandbox, err := client.Sandbox.Create(ctx, config)
	if err != nil {
		log.Fatalf("Failed to create sandbox: %v", err)
	}

	fmt.Printf("Created sandbox with JobID: %s\n", sandbox.JobID)

	// Get sandbox details
	sandbox, err = client.Sandbox.Get(ctx, sandbox.JobID)
	if err != nil {
		log.Fatalf("Failed to get sandbox: %v", err)
	}

	fmt.Printf("Sandbox config: %+v\n", sandbox.Config)

	// List all sandboxes
	sandboxes, err := client.Sandbox.List(ctx)
	if err != nil {
		log.Fatalf("Failed to list sandboxes: %v", err)
	}

	fmt.Printf("Total sandboxes: %d\n", len(sandboxes))

	// Delete sandbox when done
	err = client.Sandbox.Delete(ctx, sandbox.JobID)
	if err != nil {
		log.Fatalf("Failed to delete sandbox: %v", err)
	}

	fmt.Println("Sandbox deleted successfully!")
}
