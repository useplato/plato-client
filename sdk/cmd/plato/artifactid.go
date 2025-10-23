package main

import (
	"strings"

	plato "plato-sdk"
	"plato-sdk/models"

	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ArtifactVersion represents a simulator version/artifact
type ArtifactVersion struct {
	ArtifactID string
	Version    string
	Dataset    string
	CreatedAt  string
}

type ArtifactIDModel struct {
	client       *plato.PlatoClient
	simulator    *models.SimulatorListItem
	table        table.Model
	filterInput  textinput.Model
	allArtifacts []ArtifactVersion
	filtering    bool
	err          error
	starting     bool
}

var (
	artifactHelpStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#666666"))
)

func NewArtifactIDModel(client *plato.PlatoClient, simulator *models.SimulatorListItem) ArtifactIDModel {
	// Hardcoded artifact data matching API format
	artifacts := []ArtifactVersion{
		{
			ArtifactID: "artifact-abc123",
			Version:    "v1.2.3",
			Dataset:    "production-2024",
			CreatedAt:  "2024-01-15T10:30:00Z",
		},
		{
			ArtifactID: "artifact-def456",
			Version:    "v1.2.2",
			Dataset:    "staging-2024",
			CreatedAt:  "2024-01-10T14:20:00Z",
		},
		{
			ArtifactID: "artifact-ghi789",
			Version:    "v1.2.1",
			Dataset:    "production-2023",
			CreatedAt:  "2023-12-20T09:15:00Z",
		},
		{
			ArtifactID: "artifact-jkl012",
			Version:    "v1.2.0",
			Dataset:    "staging-2023",
			CreatedAt:  "2023-12-15T16:45:00Z",
		},
	}

	// Define table columns
	columns := []table.Column{
		{Title: "Artifact ID", Width: 20},
		{Title: "Version", Width: 12},
		{Title: "Dataset", Width: 20},
		{Title: "Created At", Width: 22},
	}

	// Convert artifacts to table rows
	rows := []table.Row{}
	for _, artifact := range artifacts {
		rows = append(rows, table.Row{
			artifact.ArtifactID,
			artifact.Version,
			artifact.Dataset,
			artifact.CreatedAt,
		})
	}

	// Create table
	t := table.New(
		table.WithColumns(columns),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(10),
	)

	// Style the table
	s := table.DefaultStyles()
	s.Header = s.Header.
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("240")).
		BorderBottom(true).
		Bold(false)
	s.Selected = s.Selected.
		Foreground(lipgloss.Color("229")).
		Background(lipgloss.Color("57")).
		Bold(false)
	t.SetStyles(s)

	// Create filter input
	filterInput := textinput.New()
	filterInput.Placeholder = "Type to filter..."
	filterInput.CharLimit = 100
	filterInput.Width = 50

	return ArtifactIDModel{
		client:       client,
		simulator:    simulator,
		table:        t,
		filterInput:  filterInput,
		allArtifacts: artifacts,
		filtering:    false,
		err:          nil,
		starting:     false,
	}
}

func (m ArtifactIDModel) Init() tea.Cmd {
	return nil
}

func (m ArtifactIDModel) Update(msg tea.Msg) (ArtifactIDModel, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		// If we're in filter mode, handle input differently
		if m.filtering {
			switch msg.String() {
			case "esc":
				// Exit filter mode
				m.filtering = false
				m.filterInput.Blur()
				return m, nil
			case "enter":
				// Exit filter mode and focus table
				m.filtering = false
				m.filterInput.Blur()
				return m, nil
			default:
				// Update filter input and refresh table
				m.filterInput, cmd = m.filterInput.Update(msg)
				m.updateTableRows()
				return m, cmd
			}
		}

		// Not in filter mode - handle normal navigation
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit

		case "/":
			// Enter filter mode
			m.filtering = true
			m.filterInput.Focus()
			return m, textinput.Blink

		case "enter":
			// Get the selected artifact from the table
			selectedRow := m.table.SelectedRow()
			if len(selectedRow) > 0 {
				artifactID := selectedRow[0] // First column is ArtifactID
				m.starting = true
				m.err = nil
				// TODO: Actually launch with artifact ID
				// For now, just go back to main menu
				_ = artifactID // Use the artifact ID when implementing launch
				return m, func() tea.Msg {
					return NavigateMsg{view: ViewMainMenu}
				}
			}
			return m, nil

		case "esc":
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewSimLaunchOptions}
			}
		}
	}

	// Update table when not filtering
	m.table, cmd = m.table.Update(msg)
	return m, cmd
}

// updateTableRows filters the artifacts and updates the table rows
func (m *ArtifactIDModel) updateTableRows() {
	filterText := strings.ToLower(strings.TrimSpace(m.filterInput.Value()))

	var rows []table.Row
	for _, artifact := range m.allArtifacts {
		// Check if any field contains the filter text
		if filterText == "" ||
			strings.Contains(strings.ToLower(artifact.ArtifactID), filterText) ||
			strings.Contains(strings.ToLower(artifact.Version), filterText) ||
			strings.Contains(strings.ToLower(artifact.Dataset), filterText) ||
			strings.Contains(strings.ToLower(artifact.CreatedAt), filterText) {
			rows = append(rows, table.Row{
				artifact.ArtifactID,
				artifact.Version,
				artifact.Dataset,
				artifact.CreatedAt,
			})
		}
	}

	m.table.SetRows(rows)
}

func (m ArtifactIDModel) View() string {
	header := RenderHeader() + "\n"

	if m.starting {
		return header + "\n  Starting environment from artifact...\n"
	}

	titleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4")).
		Bold(true).
		MarginLeft(2)

	content := header + "\n"

	// Show selected simulator name if available
	if m.simulator != nil {
		content += titleStyle.Render("Simulator: "+m.simulator.Name) + "\n\n"
	}

	content += " Select an Artifact:\n\n"

	// Show filter input if in filtering mode
	if m.filtering {
		content += " Filter: " + m.filterInput.View() + "\n\n"
	}

	content += m.table.View() + "\n\n"

	// Show different help text based on mode
	if m.filtering {
		content += " " + artifactHelpStyle.Render("Enter/Esc: Exit filter") + "\n"
	} else {
		content += " " + artifactHelpStyle.Render("↑/↓: Navigate • /: Filter • Enter: Select • Esc: Back") + "\n"
	}

	return content
}
