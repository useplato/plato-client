package main

import (
	"plato-cli/internal/ui/components"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type FlowEntryModel struct {
	inputs     []textinput.Model
	focusIndex int
	width      int
	lg         *lipgloss.Renderer
	err        string
}

type flowConfigEnteredMsg struct {
	url      string
	flowPath string
	flowName string
}

func NewFlowEntryModel(defaultURL, defaultFlowPath string) FlowEntryModel {
	inputs := make([]textinput.Model, 3)

	// URL
	inputs[0] = textinput.New()
	inputs[0].Placeholder = "http://localhost:8080"
	if defaultURL != "" {
		inputs[0].SetValue(defaultURL)
	}
	inputs[0].Focus()
	inputs[0].CharLimit = 200
	inputs[0].Width = 60

	// Flow Path
	inputs[1] = textinput.New()
	inputs[1].Placeholder = "./flows.yml or /path/to/flows.yml"
	if defaultFlowPath != "" {
		inputs[1].SetValue(defaultFlowPath)
	}
	inputs[1].CharLimit = 300
	inputs[1].Width = 60

	// Flow Name
	inputs[2] = textinput.New()
	inputs[2].SetValue("login")
	inputs[2].Placeholder = "login"
	inputs[2].CharLimit = 100
	inputs[2].Width = 60

	return FlowEntryModel{
		inputs:     inputs,
		focusIndex: 0,
		width:      100,
		lg:         lipgloss.DefaultRenderer(),
		err:        "",
	}
}

func (m FlowEntryModel) Init() tea.Cmd {
	return textinput.Blink
}

func (m FlowEntryModel) Update(msg tea.Msg) (FlowEntryModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "esc":
			// Go back to VM info
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewVMInfo}
			}
		case "tab", "shift+tab", "enter", "up", "down":
			s := msg.String()

			// Enter on last field = submit
			if s == "enter" && m.focusIndex == len(m.inputs)-1 {
				// Validate and submit
				url := strings.TrimSpace(m.inputs[0].Value())
				flowPath := strings.TrimSpace(m.inputs[1].Value())
				flowName := strings.TrimSpace(m.inputs[2].Value())

				// Validate
				if url == "" {
					m.err = "URL is required"
					return m, nil
				}
				if !strings.HasPrefix(url, "http://") && !strings.HasPrefix(url, "https://") {
					m.err = "URL must start with http:// or https://"
					return m, nil
				}
				if flowPath == "" {
					m.err = "Flow file path is required"
					return m, nil
				}
				if flowName == "" {
					m.err = "Flow name is required"
					return m, nil
				}

				return m, func() tea.Msg {
					return flowConfigEnteredMsg{
						url:      url,
						flowPath: flowPath,
						flowName: flowName,
					}
				}
			}

			// Cycle through inputs
			if s == "up" || s == "shift+tab" {
				m.focusIndex--
			} else {
				m.focusIndex++
			}

			if m.focusIndex > len(m.inputs)-1 {
				m.focusIndex = 0
			} else if m.focusIndex < 0 {
				m.focusIndex = len(m.inputs) - 1
			}

			cmds := make([]tea.Cmd, len(m.inputs))
			for i := 0; i < len(m.inputs); i++ {
				if i == m.focusIndex {
					cmds[i] = m.inputs[i].Focus()
				} else {
					m.inputs[i].Blur()
				}
			}

			return m, tea.Batch(cmds...)
		default:
			// Clear error on new input
			m.err = ""
		}
	}

	// Update focused input
	cmd := m.updateInputs(msg)
	return m, cmd
}

func (m *FlowEntryModel) updateInputs(msg tea.Msg) tea.Cmd {
	cmds := make([]tea.Cmd, len(m.inputs))
	for i := range m.inputs {
		m.inputs[i], cmds[i] = m.inputs[i].Update(msg)
	}
	return tea.Batch(cmds...)
}

func (m FlowEntryModel) View() string {
	headerStyle := m.lg.NewStyle().
		Foreground(lipgloss.AdaptiveColor{Light: "#5A56E0", Dark: "#7571F9"}).
		Bold(true).
		Padding(0, 1, 0, 2)

	header := headerStyle.Render("Run Flow Configuration")

	labelStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("205")).
		MarginLeft(2).
		MarginTop(1)

	inputStyle := m.lg.NewStyle().
		MarginLeft(2)

	helpStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("240")).
		MarginTop(2).
		MarginLeft(2)

	errorStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("196")).
		MarginLeft(2).
		MarginTop(1)

	labels := []string{
		"Target URL:",
		"Flow File Path:",
		"Flow Name:",
	}

	var body strings.Builder
	body.WriteString("\n")

	for i, input := range m.inputs {
		body.WriteString(labelStyle.Render(labels[i]))
		body.WriteString("\n")
		body.WriteString(inputStyle.Render(input.View()))
		body.WriteString("\n")
	}

	if m.err != "" {
		body.WriteString("\n")
		body.WriteString(errorStyle.Render("⚠ " + m.err))
	}

	body.WriteString("\n")
	body.WriteString(helpStyle.Render("tab/shift+tab: navigate • enter: submit • esc: back"))

	return components.RenderHeader() + "\n" + header + "\n" + body.String()
}
