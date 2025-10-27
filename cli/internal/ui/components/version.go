// Package components provides reusable UI components for the Plato CLI.
//
// This file provides version information and header rendering.
package components

import (
	"fmt"
	"os"

	"github.com/charmbracelet/lipgloss"
)

// Build information - these are set via ldflags during build
var (
	Version   = "dev"
	GitCommit = "unknown"
	BuildTime = "unknown"
)

// RenderHeader renders the CLI header with version information
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
	versionInfo := fmt.Sprintf("v%s", Version)
	if GitCommit != "unknown" && len(GitCommit) > 7 {
		versionInfo += fmt.Sprintf(" (%s)", GitCommit[:7])
	}

	title := titleStyle.Render("Plato Sandbox CLI")
	subtitle := subtitleStyle.Render(fmt.Sprintf("%s · %s", versionInfo, cwd))

	return fmt.Sprintf("%s\n%s\n", title, subtitle)
}
