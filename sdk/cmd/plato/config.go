// Package main provides the configuration management view for the Plato CLI.
//
// This file implements the ConfigModel which handles loading and displaying
// API configuration from environment variables and .env files. It shows the
// current API key and base URL settings to the user.
package main

import (

"plato-sdk/cmd/plato/internal/ui/components"
	"os"
	"strings"
	plato "plato-sdk"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/joho/godotenv"
)

type ConfigModel struct {
	client *plato.PlatoClient
}

func NewConfigModel() ConfigModel {
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

	client := plato.NewClient(apiKey, opts...)

	return ConfigModel{
		client: client,
	}
}

func (m ConfigModel) Init() tea.Cmd {
	return nil
}

func (m ConfigModel) Update(msg tea.Msg) (ConfigModel, tea.Cmd) {
	return m, nil
}

func (m ConfigModel) View() string {
	labelStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4")).
		Bold(true).
		Width(12)

	valueStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#FAFAFA"))

	notSetStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#888888")).
		Italic(true)

	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666")).
		MarginTop(2)

	containerStyle := lipgloss.NewStyle().
		MarginLeft(2).
		MarginTop(1)

	apiKey := m.client.GetAPIKey()
	baseURL := m.client.GetBaseURL()

	var content strings.Builder
	content.WriteString(components.RenderHeader())
	content.WriteString("\n")

	// API Key
	content.WriteString(containerStyle.Render(labelStyle.Render("API Key:")))
	content.WriteString(" ")
	if apiKey == "" {
		content.WriteString(notSetStyle.Render("Not set"))
	} else {
		content.WriteString(valueStyle.Render(apiKey))
	}
	content.WriteString("\n")

	// Base URL
	content.WriteString(containerStyle.Render(labelStyle.Render("Base URL:")))
	content.WriteString(" ")
	content.WriteString(valueStyle.Render(baseURL))
	content.WriteString("\n")

	content.WriteString(helpStyle.Render("  Press 'esc' or 'q' to go back"))

	return content.String()
}
