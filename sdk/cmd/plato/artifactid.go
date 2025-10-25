package main

import (

"plato-sdk/cmd/plato/internal/ui/components"
	"context"
	"strings"
	plato "plato-sdk"
	"plato-sdk/models"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type ArtifactIDModel struct {
	client       *plato.PlatoClient
	simulator    *models.SimulatorListItem
	table        table.Model
	filterInput  textinput.Model
	allArtifacts []*models.SimulatorVersion
	filtering    bool
	loading      bool
	err          error
	starting     bool
}

type versionsLoadedMsg struct {
	versions []*models.SimulatorVersion
	err      error
}

var (
	artifactHelpStyle = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#666666"))
)

func loadVersions(client *plato.PlatoClient, simulatorName string) tea.Cmd {
	return func() tea.Msg {
		versions, err := client.Simulator.GetVersions(context.Background(), simulatorName)
		return versionsLoadedMsg{versions: versions, err: err}
	}
}

func NewArtifactIDModel(client *plato.PlatoClient, simulator *models.SimulatorListItem) ArtifactIDModel {

	// Define table columns
	columns := []table.Column{
		{Title: "Artifact ID", Width: 20},
		{Title: "Version", Width: 12},
		{Title: "Dataset", Width: 20},
		{Title: "Created At", Width: 22},
	}

	// Create table with empty rows initially
	t := table.New(
		table.WithColumns(columns),
		table.WithRows([]table.Row{}),
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
		allArtifacts: []*models.SimulatorVersion{},
		filtering:    false,
		loading:      true,
		err:          nil,
		starting:     false,
	}
}

func (m ArtifactIDModel) Init() tea.Cmd {
	if m.simulator != nil {
		return loadVersions(m.client, m.simulator.Name)
	}
	return nil
}

func (m ArtifactIDModel) Update(msg tea.Msg) (ArtifactIDModel, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case versionsLoadedMsg:
		m.loading = false
		if msg.err != nil {
			m.err = msg.err
			return m, nil
		}
		m.allArtifacts = msg.versions
		m.updateTableRows()
		return m, nil

	case tea.KeyMsg:
		// Don't process keys while loading
		if m.loading {
			return m, nil
		}

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
				version := selectedRow[1]     // Second column is Version
				dataset := selectedRow[2]     // Third column is Dataset
				m.starting = true
				m.err = nil
				// Launch environment with the selected artifact ID, version, and dataset
				return m, func() tea.Msg {
					return launchEnvironmentMsg{simulator: m.simulator, artifactID: &artifactID, version: &version, dataset: &dataset}
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
	header := components.RenderHeader() + "\n"

	if m.starting {
		return header + "\n  Starting environment from artifact...\n"
	}

	titleStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4")).
		Bold(true).
		MarginLeft(2)

	loadingStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#888888")).
		MarginLeft(2)

	errorStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#FF0000")).
		MarginLeft(2)

	content := header + "\n"

	// Show selected simulator name if available
	if m.simulator != nil {
		content += titleStyle.Render("Simulator: "+m.simulator.Name) + "\n\n"
	}

	if m.loading {
		content += loadingStyle.Render("Loading versions...")
		return content
	}

	if m.err != nil {
		content += errorStyle.Render("Error: " + m.err.Error())
		return content
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
