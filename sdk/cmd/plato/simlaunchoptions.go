package main

import (
	plato "plato-sdk"
	"plato-sdk/models"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type SimLaunchOptionsModel struct {
	client     *plato.PlatoClient
	simulator  *models.SimulatorListItem
	list       list.Model
}

type simLaunchOption struct {
	title       string
	description string
}

func (s simLaunchOption) Title() string       { return s.title }
func (s simLaunchOption) Description() string { return s.description }
func (s simLaunchOption) FilterValue() string { return s.title }

type navigateToArtifactIDMsg struct {
	simulator *models.SimulatorListItem
}

type launchEnvironmentMsg struct {
	simulator  *models.SimulatorListItem
	artifactID *string
	version    *string
}

func NewSimLaunchOptionsModel(client *plato.PlatoClient, simulator *models.SimulatorListItem) SimLaunchOptionsModel {
	items := []list.Item{
		simLaunchOption{
			title:       "Launch Latest",
			description: "Launch the latest version of this simulator",
		},
		simLaunchOption{
			title:       "By Artifact ID",
			description: "Select a specific version by artifact ID",
		},
	}

	l := list.New(items, list.NewDefaultDelegate(), 80, 10)
	l.Title = "Launch Options"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(false)
	l.SetShowHelp(false)

	return SimLaunchOptionsModel{
		client:    client,
		simulator: simulator,
		list:      l,
	}
}

func (m SimLaunchOptionsModel) Init() tea.Cmd {
	return nil
}

func (m SimLaunchOptionsModel) Update(msg tea.Msg) (SimLaunchOptionsModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.list.SetSize(msg.Width, 10)
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "enter":
			selectedItem := m.list.SelectedItem()
			if selectedItem != nil {
				option := selectedItem.(simLaunchOption)
				switch option.title {
				case "Launch Latest":
					// Launch environment with latest version (no artifact ID)
					return m, func() tea.Msg {
						return launchEnvironmentMsg{simulator: m.simulator, artifactID: nil, version: nil}
					}
				case "By Artifact ID":
					// Navigate to artifact ID selection for this simulator
					return m, func() tea.Msg {
						return navigateToArtifactIDMsg{simulator: m.simulator}
					}
				}
			}
			return m, nil

		case "esc", "q":
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewSimSelector}
			}
		}
	}

	var cmd tea.Cmd
	m.list, cmd = m.list.Update(msg)
	return m, cmd
}

func (m SimLaunchOptionsModel) View() string {
	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666")).
		MarginLeft(2).
		MarginTop(1)

	titleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4")).
		Bold(true).
		MarginLeft(2).
		MarginBottom(1)

	var content string
	content += RenderHeader() + "\n"

	// Show selected simulator name
	if m.simulator != nil {
		content += titleStyle.Render("Simulator: " + m.simulator.Name) + "\n\n"
	}

	content += m.list.View() + "\n"
	content += helpStyle.Render("Enter: Select • Esc/q: Back")

	return content
}
