// Package main provides the plato-config.yml loader view for the Plato CLI.
//
// This file implements the PlatoConfigModel which reads and parses a local
// plato-config.yml file, then presents the available datasets to the user
// for launching as VM sandboxes. This allows users to launch VMs from their
// local simulator configurations.
package main

import (

"plato-cli/internal/ui/components"
	"fmt"
	plato "plato-sdk"
	"plato-sdk/models"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type PlatoConfigModel struct {
	client      *plato.PlatoClient
	config      *models.PlatoConfig
	datasetList list.Model
	loading     bool
	err         error
	width       int
}

type launchFromConfigMsg struct {
	datasetName   string
	datasetConfig models.SimConfigDataset
	service       string
}

type datasetItem struct {
	name   string
	config models.SimConfigDataset
}

func (d datasetItem) Title() string       { return d.name }
func (d datasetItem) Description() string {
	return fmt.Sprintf("CPUs: %d, Memory: %dMB, Disk: %dMB",
		d.config.Compute.Cpus,
		d.config.Compute.Memory,
		d.config.Compute.Disk)
}
func (d datasetItem) FilterValue() string { return d.name }

func NewPlatoConfigModel(client *plato.PlatoClient) PlatoConfigModel {
	return PlatoConfigModel{
		client:  client,
		loading: true,
		width:   80,
	}
}

func loadConfig() tea.Msg {
	config, err := LoadPlatoConfig()
	if err != nil {
		return configLoadedMsg{err: err}
	}
	return configLoadedMsg{config: config}
}

type configLoadedMsg struct {
	config *models.PlatoConfig
	err    error
}

func (m PlatoConfigModel) Init() tea.Cmd {
	return loadConfig
}

func (m PlatoConfigModel) Update(msg tea.Msg) (PlatoConfigModel, tea.Cmd) {
	switch msg := msg.(type) {
	case configLoadedMsg:
		m.loading = false
		if msg.err != nil {
			m.err = msg.err
			return m, nil
		}

		m.config = msg.config

		// Build list of datasets
		items := []list.Item{}
		if m.config.Datasets != nil {
			for name, dataset := range *m.config.Datasets {
				items = append(items, datasetItem{
					name:   name,
					config: dataset,
				})
			}
		}

		l := list.New(items, list.NewDefaultDelegate(), 80, 12)
		l.Title = "Select Dataset"
		l.SetShowStatusBar(false)
		l.SetFilteringEnabled(false)
		l.SetShowHelp(false)
		m.datasetList = l

		return m, nil

	case tea.WindowSizeMsg:
		m.width = msg.Width
		if !m.loading && m.config != nil {
			h := 12
			m.datasetList.SetSize(msg.Width, h)
		}
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "enter":
			if !m.loading && m.config != nil {
				selectedItem := m.datasetList.SelectedItem()
				if selectedItem != nil {
					dataset := selectedItem.(datasetItem)
					// Navigate to VMConfigModel with the dataset config
					service := ""
					if m.config.Service != nil {
						service = *m.config.Service
					}
					return m, func() tea.Msg {
						return launchFromConfigMsg{
							datasetName:   dataset.name,
							datasetConfig: dataset.config,
							service:       service,
						}
					}
				}
			}
			return m, nil

		case "esc":
			// If there's an error, clear it first
			if m.err != nil {
				m.err = nil
				// Reload config
				return m, loadConfig
			}
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewLaunchEnvironment}
			}
		}
	}

	if !m.loading && m.config != nil {
		var cmd tea.Cmd
		m.datasetList, cmd = m.datasetList.Update(msg)
		return m, cmd
	}

	return m, nil
}

func (m PlatoConfigModel) View() string {
	if m.err != nil {
		errorStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF0000")).
			Bold(true).
			Padding(2, 4).
			Width(m.width - 10).
			BorderStyle(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#FF0000"))

		helpStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#666666")).
			Padding(1, 4)

		errorMsg := fmt.Sprintf("❌ Error:\n\n%v", m.err)
		help := "Press Esc to go back"

		return components.RenderHeader() + "\n" + errorStyle.Render(errorMsg) + "\n" + helpStyle.Render(help)
	}

	if m.loading {
		style := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#888888")).
			Padding(2, 4)
		return components.RenderHeader() + "\n" + style.Render("Loading plato-config.yml...")
	}

	if m.config == nil || m.config.Datasets == nil || len(*m.config.Datasets) == 0 {
		style := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#888888")).
			Padding(2, 4)
		return components.RenderHeader() + "\n" + style.Render("No datasets found in plato-config.yml")
	}

	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666")).
		MarginLeft(2).
		MarginTop(1)

	content := components.RenderHeader() + "\n" + m.datasetList.View()
	content += "\n" + helpStyle.Render("Enter: Launch • Esc: Back")
	return content
}
