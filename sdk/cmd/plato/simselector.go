// Package main provides the simulator selector view for the Plato CLI.
//
// This file implements the SimSelectorModel which displays a searchable list
// of available simulators that users can select to launch as environments.
// It fetches simulator data from the Plato API and provides filtering capabilities.
package main

import (

"plato-sdk/cmd/plato/internal/ui/components"
	"context"
	"fmt"
	"io"
	"strings"
	plato "plato-sdk"
	"plato-sdk/models"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type SimSelectorModel struct {
	client   *plato.PlatoClient
	list     list.Model
	loading  bool
	err      error
	choice   *models.SimulatorListItem
}

type simItem struct {
	sim *models.SimulatorListItem
}

func (s simItem) FilterValue() string { return s.sim.Name }
func (s simItem) Title() string       { return s.sim.Name }
func (s simItem) Description() string {
	if s.sim.Description != nil {
		return *s.sim.Description
	}
	return fmt.Sprintf("Type: %s • Version: %s", s.sim.SimType, s.sim.VersionTag)
}

type simulatorsLoadedMsg struct {
	simulators []*models.SimulatorListItem
	err        error
}

type navigateToSimLaunchOptionsMsg struct {
	simulator *models.SimulatorListItem
}

func loadSimulators(client *plato.PlatoClient) tea.Cmd {
	return func() tea.Msg {
		sims, err := client.Simulator.List(context.Background())
		return simulatorsLoadedMsg{simulators: sims, err: err}
	}
}

type simItemDelegate struct{}

func (d simItemDelegate) Height() int                             { return 2 }
func (d simItemDelegate) Spacing() int                            { return 1 }
func (d simItemDelegate) Update(_ tea.Msg, _ *list.Model) tea.Cmd { return nil }
func (d simItemDelegate) Render(w io.Writer, m list.Model, index int, listItem list.Item) {
	i, ok := listItem.(simItem)
	if !ok {
		return
	}

	var (
		titleStyle    = lipgloss.NewStyle().PaddingLeft(4)
		selectedStyle = lipgloss.NewStyle().PaddingLeft(2).Foreground(lipgloss.Color("#7D56F4"))
		descStyle     = lipgloss.NewStyle().PaddingLeft(4).Foreground(lipgloss.Color("#666666"))
	)

	title := i.Title()
	desc := i.Description()

	if index == m.Index() {
		title = selectedStyle.Render("> " + title)
		desc = selectedStyle.Render("  " + desc)
	} else {
		title = titleStyle.Render(title)
		desc = descStyle.Render(desc)
	}

	fmt.Fprintf(w, "%s\n%s", title, desc)
}

func NewSimSelectorModel(client *plato.PlatoClient) SimSelectorModel {
	l := list.New([]list.Item{}, simItemDelegate{}, 80, 20)
	l.Title = "Select Simulator"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(true)
	l.SetShowHelp(false)

	return SimSelectorModel{
		client:  client,
		list:    l,
		loading: true,
		err:     nil,
		choice:  nil,
	}
}

func (m SimSelectorModel) Init() tea.Cmd {
	return loadSimulators(m.client)
}

func (m SimSelectorModel) Update(msg tea.Msg) (SimSelectorModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.list.SetSize(msg.Width, 20)
		return m, nil

	case simulatorsLoadedMsg:
		m.loading = false
		if msg.err != nil {
			m.err = msg.err
			return m, nil
		}

		// Filter only enabled simulators
		items := []list.Item{}
		for _, sim := range msg.simulators {
			if sim.Enabled {
				items = append(items, simItem{sim: sim})
			}
		}
		m.list.SetItems(items)
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "q":
			// Only go back if NOT filtering (so you can type 'q' in filter)
			if m.list.FilterState() != list.Filtering {
				return m, func() tea.Msg {
					return NavigateMsg{view: ViewLaunchEnvironment}
				}
			}
		case "enter":
			if !m.loading && m.err == nil {
				selectedItem := m.list.SelectedItem()
				if selectedItem != nil {
					item := selectedItem.(simItem)
					m.choice = item.sim
					// Navigate to launch options for this simulator
					return m, func() tea.Msg {
						return navigateToSimLaunchOptionsMsg{simulator: item.sim}
					}
				}
			}
			return m, nil
		case "esc":
			// If filtering, clear the filter
			if m.list.FilterState() == list.Filtering || m.list.FilterState() == list.FilterApplied {
				m.list.ResetFilter()
				return m, nil
			}
			// If not filtering, go back
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewLaunchEnvironment}
			}
		}
	}

	var cmd tea.Cmd
	m.list, cmd = m.list.Update(msg)
	return m, cmd
}

func (m SimSelectorModel) View() string {
	helpStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666")).
		MarginLeft(2).
		MarginTop(1)

	var content strings.Builder
	content.WriteString(components.RenderHeader() + "\n")

	if m.loading {
		loadingStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#888888")).
			MarginLeft(2)
		content.WriteString(loadingStyle.Render("Loading simulators..."))
		return content.String()
	}

	if m.err != nil {
		errorStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF0000")).
			MarginLeft(2)
		content.WriteString(errorStyle.Render(fmt.Sprintf("Error: %s", m.err.Error())))
		return content.String()
	}

	content.WriteString(m.list.View())
	content.WriteString("\n")
	content.WriteString(helpStyle.Render("Enter: Select • /: Filter • Esc/q: Back"))

	return content.String()
}
