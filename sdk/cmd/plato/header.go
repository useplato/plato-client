package main

import (
	"fmt"
	"os"

	"github.com/charmbracelet/lipgloss"
)

// Build information - these are set via ldflags during build
var (
	version   = "dev"
	gitCommit = "unknown"
	buildTime = "unknown"
)

func RenderHeader() string {
	titleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4")).
		Bold(true).
		MarginTop(1).
		MarginBottom(0).
		MarginLeft(2)

	subtitleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#888888")).
		MarginLeft(2).
		MarginBottom(1)

	// Get current working directory
	cwd, err := os.Getwd()
	if err != nil {
		cwd = "unknown"
	}

	// Build version info string
	versionInfo := fmt.Sprintf("v%s", version)
	if gitCommit != "unknown" && len(gitCommit) > 7 {
		versionInfo += fmt.Sprintf(" (%s)", gitCommit[:7])
	}

	title := titleStyle.Render("Plato Sandbox CLI")
	subtitle := subtitleStyle.Render(fmt.Sprintf("%s · %s", versionInfo, cwd))

	return fmt.Sprintf("%s\n%s\n", title, subtitle)
}
