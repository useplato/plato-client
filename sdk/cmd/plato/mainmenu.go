// Package main provides the main menu view for the Plato CLI.
//
// This file implements the MainMenuModel which displays the primary navigation
// menu with options to launch environments, view configuration, or quit the CLI.
package main

import (
	"os"

	"plato-cli/internal/ui/components"

	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type MainMenuModel struct {
	choices      list.Model
	apiKeyMissing bool
}

type menuItem struct {
	title       string
	description string
}

func (i menuItem) Title() string       { return i.title }
func (i menuItem) Description() string { return i.description }
func (i menuItem) FilterValue() string { return i.title }

func NewMainMenuModel() MainMenuModel {
	items := []list.Item{
		menuItem{title: "Launch Environment", description: "Start from an existing environment or a blank slate."},
		menuItem{title: "Configuration", description: "View API key and settings"},
		menuItem{title: "Quit", description: "Exit the CLI"},
	}

	l := list.New(items, list.NewDefaultDelegate(), 80, 15)
	l.Title = "Main Menu"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(false)

	// Check if API key is set
	apiKey := os.Getenv("PLATO_API_KEY")

	return MainMenuModel{
		choices:      l,
		apiKeyMissing: apiKey == "",
	}
}

func (m MainMenuModel) Init() tea.Cmd {
	return nil
}

func (m MainMenuModel) Update(msg tea.Msg) (MainMenuModel, tea.Cmd) {
	// If API key is missing, only allow quitting with any key
	if m.apiKeyMissing {
		if _, ok := msg.(tea.KeyMsg); ok {
			return m, tea.Quit
		}
		return m, nil
	}

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		h := 15 // Fixed reasonable height for menu items
		m.choices.SetSize(msg.Width, h)
		return m, nil
	case tea.KeyMsg:
		switch {
		case key.Matches(msg, key.NewBinding(key.WithKeys("enter"))):
			// Handle selection
			selectedItem := m.choices.SelectedItem()
			if selectedItem != nil {
				item := selectedItem.(menuItem)
				switch item.title {
				case "Launch Environment":
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewLaunchEnvironment}
					}
				case "Configuration":
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewConfig}
					}
				case "Quit":
					return m, tea.Quit
				}
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.choices, cmd = m.choices.Update(msg)
	return m, cmd
}

func (m MainMenuModel) View() string {
	header := components.RenderHeader() + "\n"

	// If API key is missing, show error message and exit instructions
	if m.apiKeyMissing {
		warningStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF0000")).
			Bold(true).
			MarginLeft(2).
			MarginTop(1).
			MarginBottom(1)

		instructionStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#CCCCCC")).
			MarginLeft(2).
			MarginBottom(1)

		exitStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#888888")).
			MarginLeft(2).
			MarginTop(2)

		warning := warningStyle.Render("⚠  PLATO_API_KEY is not set")
		instructions := instructionStyle.Render(
			"Please set your API key before using the CLI:\n\n" +
			"  export PLATO_API_KEY=your-api-key-here\n\n" +
			"Or create a .env file in your project directory with:\n\n" +
			"  PLATO_API_KEY=your-api-key-here\n\n" +
			"You can view your API key at: https://plato.so/settings",
		)
		exitMsg := exitStyle.Render("Press any key to exit...")

		return header + warning + "\n" + instructions + "\n" + exitMsg
	}

	return header + m.choices.View()
}
