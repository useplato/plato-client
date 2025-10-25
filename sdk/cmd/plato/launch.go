// Package main provides the environment launch view for the Plato CLI.
//
// This file implements the LaunchModel which handles the environment launch
// workflow, allowing users to choose between launching from an existing simulator,
// launching from a local plato-config.yml, or creating a blank VM.
package main

import (

"plato-sdk/cmd/plato/internal/ui/components"
	plato "plato-sdk"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type LaunchModel struct {
	client      *plato.PlatoClient
	optionsList list.Model
}

type launchOption struct {
	title       string
	description string
	disabled    bool
}

func (l launchOption) Title() string       { return l.title }
func (l launchOption) Description() string {
	if l.disabled {
		return l.description + " (unavailable)"
	}
	return l.description
}
func (l launchOption) FilterValue() string { return l.title }

func NewLaunchModel(client *plato.PlatoClient) LaunchModel {
	configExists := ConfigExists()

	var configOption launchOption
	if configExists {
		configOption = launchOption{
			title:       "Launch from Plato Config",
			description: "Launch from plato-config.yml in current directory",
			disabled:    false,
		}
	} else {
		configOption = launchOption{
			title:       "Launch from Plato Config",
			description: "Please create config first or start with a blank VM",
			disabled:    true,
		}
	}

	items := []list.Item{
		launchOption{title: "Launch Blank VM", description: "Configure and launch a fresh virtual machine", disabled: false},
		configOption,
		launchOption{title: "Resume From Existing Artifact", description: "Launch an existing environment by name", disabled: false},
	}

	l := list.New(items, list.NewDefaultDelegate(), 80, 15)
	l.Title = "Launch Options"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(false)
	l.SetShowHelp(false)

	return LaunchModel{
		client:      client,
		optionsList: l,
	}
}

func (m LaunchModel) Init() tea.Cmd {
	return nil
}

func (m LaunchModel) Update(msg tea.Msg) (LaunchModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		h := 12 // Fixed reasonable height for 3 items
		m.optionsList.SetSize(msg.Width, h)
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "enter":
			selectedItem := m.optionsList.SelectedItem()
			if selectedItem != nil {
				option := selectedItem.(launchOption)
				// Don't allow selecting disabled options
				if option.disabled {
					return m, nil
				}
				switch option.title {
				case "Launch Blank VM":
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewVMConfig}
					}
				case "Launch from Plato Config":
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewPlatoConfig}
					}
				case "Resume From Existing Artifact":
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewSimSelector}
					}
				}
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.optionsList, cmd = m.optionsList.Update(msg)
	return m, cmd
}

func (m LaunchModel) View() string {
	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666")).
		MarginLeft(2).
		MarginTop(1)

	content := components.RenderHeader() + "\n" + m.optionsList.View()
	content += "\n" + helpStyle.Render("Enter: Select • Esc: Back to Main Menu")
	return content
}
