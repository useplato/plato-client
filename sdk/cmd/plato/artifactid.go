package main

import (
	"strings"

	plato "plato-sdk"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type ArtifactIDModel struct {
	client   *plato.PlatoClient
	input    textinput.Model
	err      error
	starting bool
}

var (
	artifactLabelStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#7D56F4")).
				Width(15)
	artifactHelpStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#666666"))
	artifactErrorStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#FF0000"))
	artifactFocusedStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#7D56F4"))
)

func NewArtifactIDModel(client *plato.PlatoClient) ArtifactIDModel {
	input := textinput.New()
	input.Placeholder = "artifact-abc123..."
	input.Focus()
	input.CharLimit = 100
	input.Width = 50
	input.Prompt = ""
	input.TextStyle = artifactFocusedStyle
	input.PromptStyle = artifactFocusedStyle

	return ArtifactIDModel{
		client:   client,
		input:    input,
		err:      nil,
		starting: false,
	}
}

func (m ArtifactIDModel) Init() tea.Cmd {
	return textinput.Blink
}

func (m ArtifactIDModel) Update(msg tea.Msg) (ArtifactIDModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit

		case "enter":
			artifactID := strings.TrimSpace(m.input.Value())
			if artifactID == "" {
				m.err = nil // Clear error if they just press enter with empty
				return m, nil
			}

			// Validate artifact ID format (basic check)
			if len(artifactID) < 5 {
				m.err = nil // Will show in validation below
				return m, nil
			}

			m.starting = true
			m.err = nil
			// TODO: Actually launch with artifact ID
			// For now, just go back to main menu
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewMainMenu}
			}

		case "esc":
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewLaunchEnvironment}
			}
		}
	}

	var cmd tea.Cmd
	m.input, cmd = m.input.Update(msg)
	return m, cmd
}

func (m ArtifactIDModel) View() string {
	var content strings.Builder
	content.WriteString(RenderHeader() + "\n")

	if m.starting {
		content.WriteString("\n  Starting environment from artifact...\n")
		return content.String()
	}

	content.WriteString("\n Launch by Artifact ID:\n\n")
	content.WriteString(" " + artifactLabelStyle.Render("Artifact ID") + "\n")
	content.WriteString(" " + m.input.View() + "\n")

	if m.err != nil {
		content.WriteString("\n " + artifactErrorStyle.Render("⚠ "+m.err.Error()) + "\n")
	}

	content.WriteString("\n " + artifactHelpStyle.Render("Enter: Start • Esc: Back") + "\n")

	return content.String()
}
