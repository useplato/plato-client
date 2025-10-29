package main

import (
	"fmt"
	"plato-cli/internal/ui/components"
	"plato-sdk/models"
	"strings"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type DatasetSelectorModel struct {
	service        string
	config         *models.PlatoConfig
	list           list.Model
	width          int
	lg             *lipgloss.Renderer
	err            string
	snapshotParams snapshotParams
}

type snapshotParams struct {
	publicID         string
	jobGroupID       string
	service          string
	lastPushedBranch string
}

type datasetOption struct {
	name        string
	description string
	dataset     models.SimConfigDataset
}

func (d datasetOption) Title() string       { return d.name }
func (d datasetOption) Description() string { return d.description }
func (d datasetOption) FilterValue() string { return d.name }

type datasetSelectedMsg struct {
	datasetName   string
	datasetConfig models.SimConfigDataset
	params        snapshotParams
}

type refreshDatasetsMsg struct{}

func NewDatasetSelectorModel(service string, params snapshotParams) DatasetSelectorModel {
	// Load config
	config, err := LoadPlatoConfig()

	var items []list.Item
	var errMsg string

	if err != nil {
		errMsg = fmt.Sprintf("Failed to load plato-config.yml: %v", err)
	} else {
		// Build dataset options
		if config.Datasets != nil {
			for name, dataset := range *config.Datasets {
				// Build description with listener info
				var desc strings.Builder
				desc.WriteString(fmt.Sprintf("%dCPU/%dMB", dataset.Compute.Cpus, dataset.Compute.Memory))

				// Add listener info from Listeners map
				if dataset.Listeners != nil && len(*dataset.Listeners) > 0 {
					desc.WriteString(" • Listeners: ")
					listenerNames := []string{}
					for listenerName := range *dataset.Listeners {
						listenerNames = append(listenerNames, listenerName)
					}
					desc.WriteString(strings.Join(listenerNames, ", "))
				}

				items = append(items, datasetOption{
					name:        name,
					description: desc.String(),
					dataset:     dataset,
				})
			}
		}

		// Add refresh option at the end
		items = append(items, datasetOption{
			name:        "🔄 Refresh Datasets",
			description: "Reload plato-config.yml to see updated datasets",
			dataset:     models.SimConfigDataset{},
		})
	}

	l := list.New(items, list.NewDefaultDelegate(), 80, 20)
	l.Title = fmt.Sprintf("Select Dataset to Snapshot as (%s)", service)
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(true)
	l.SetShowHelp(false)

	return DatasetSelectorModel{
		service:        service,
		config:         config,
		list:           l,
		width:          100,
		lg:             lipgloss.DefaultRenderer(),
		err:            errMsg,
		snapshotParams: params,
	}
}

func (m DatasetSelectorModel) Init() tea.Cmd {
	return nil
}

func (m DatasetSelectorModel) Update(msg tea.Msg) (DatasetSelectorModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.list.SetSize(msg.Width, 20)
		return m, nil

	case refreshDatasetsMsg:
		// Reload the config and rebuild the model
		newModel := NewDatasetSelectorModel(m.service, m.snapshotParams)
		return newModel, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "esc":
			// Go back to VM info
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewVMInfo}
			}
		case "enter":
			selectedItem := m.list.SelectedItem()
			if selectedItem != nil {
				option := selectedItem.(datasetOption)

				// Check if refresh option was selected
				if option.name == "🔄 Refresh Datasets" {
					return m, func() tea.Msg {
						return refreshDatasetsMsg{}
					}
				}

				// Dataset selected, proceed with snapshot
				return m, func() tea.Msg {
					return datasetSelectedMsg{
						datasetName:   option.name,
						datasetConfig: option.dataset,
						params:        m.snapshotParams,
					}
				}
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.list, cmd = m.list.Update(msg)
	return m, cmd
}

func (m DatasetSelectorModel) View() string {
	headerStyle := m.lg.NewStyle().
		Foreground(lipgloss.AdaptiveColor{Light: "#5A56E0", Dark: "#7571F9"}).
		Bold(true).
		Padding(0, 1, 0, 2)

	header := headerStyle.Render("Select Dataset for Snapshot")

	helpStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("240")).
		MarginTop(1).
		MarginLeft(2)

	errorStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("196")).
		MarginLeft(2).
		MarginTop(1)

	var body strings.Builder
	body.WriteString("\n")

	if m.err != "" {
		body.WriteString(errorStyle.Render("⚠ " + m.err))
		body.WriteString("\n\n")
		body.WriteString(helpStyle.Render("esc: back"))
	} else {
		body.WriteString(m.list.View())
		body.WriteString("\n")
		body.WriteString(helpStyle.Render("↑/↓: navigate • enter: select • /: filter • esc: back"))
	}

	return components.RenderHeader() + "\n" + header + "\n" + body.String()
}
