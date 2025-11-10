package main

import (
	"plato-cli/internal/ui/components"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type AdvancedMenuModel struct {
	publicID      string
	sshHost       string
	sshConfigPath string
	actionList    list.Model
	width         int
	lg            *lipgloss.Renderer
}

type advancedAction struct {
	title       string
	description string
}

func (a advancedAction) Title() string       { return a.title }
func (a advancedAction) Description() string { return a.description }
func (a advancedAction) FilterValue() string { return a.title }

type executeAdvancedActionMsg struct {
	action string
}

func NewAdvancedMenuModel(publicID, sshHost, sshConfigPath string) AdvancedMenuModel {
	items := []list.Item{
		advancedAction{title: "Authenticate ECR", description: "Authenticate Docker with AWS ECR on the VM"},
		advancedAction{title: "Open Proxytunnel", description: "Create local port forward to VM"},
		advancedAction{title: "Audit Ignore UI", description: "Configure ignore_tables via web UI"},
		advancedAction{title: "Run Flow", description: "Execute a test flow against the VM"},
		advancedAction{title: "Get State", description: "Print the current simulator state"},
		advancedAction{title: "Create Checkpoint", description: "Create a checkpoint of current VM state"},
		advancedAction{title: "Set up root SSH", description: "Configure root SSH password access"},
		advancedAction{title: "Back", description: "Return to main menu"},
	}

	l := list.New(items, list.NewDefaultDelegate(), 50, 12)
	l.Title = "Advanced Options"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(false)
	l.SetShowHelp(false)
	l.SetShowPagination(false)

	return AdvancedMenuModel{
		publicID:      publicID,
		sshHost:       sshHost,
		sshConfigPath: sshConfigPath,
		actionList:    l,
		width:         100,
		lg:            lipgloss.DefaultRenderer(),
	}
}

func (m AdvancedMenuModel) Init() tea.Cmd {
	return nil
}

func (m AdvancedMenuModel) Update(msg tea.Msg) (AdvancedMenuModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width

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
			selectedItem := m.actionList.SelectedItem()
			if selectedItem != nil {
				action := selectedItem.(advancedAction)
				if action.title == "Back" {
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewVMInfo}
					}
				}
				// Send message to execute the action in the VMInfo model
				return m, func() tea.Msg {
					return executeAdvancedActionMsg{action: action.title}
				}
			}
		}
	}

	// Update action list
	var cmd tea.Cmd
	m.actionList, cmd = m.actionList.Update(msg)
	return m, cmd
}

func (m AdvancedMenuModel) View() string {
	headerStyle := m.lg.NewStyle().
		Foreground(lipgloss.AdaptiveColor{Light: "#5A56E0", Dark: "#7571F9"}).
		Bold(true).
		Padding(0, 1, 0, 2)

	header := headerStyle.Render("Advanced VM Management")

	body := m.lg.NewStyle().
		Margin(1, 4, 1, 0).
		Render(m.actionList.View())

	helpStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("240")).
		MarginTop(1).
		MarginLeft(2)

	footer := helpStyle.Render("enter: select • esc: back to main menu • ctrl+c: quit")

	return components.RenderHeader() + "\n" + header + "\n" + body + "\n" + footer
}
