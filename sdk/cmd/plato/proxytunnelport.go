package main

import (

"plato-cli/internal/ui/components"
	"strconv"
	"strings"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type ProxytunnelPortModel struct {
	publicID  string
	textInput textinput.Model
	width     int
	lg        *lipgloss.Renderer
	err       string
}

type openTunnelMsg struct {
	publicID   string
	remotePort int
}

func NewProxytunnelPortModel(publicID string) ProxytunnelPortModel {
	ti := textinput.New()
	ti.Placeholder = "Enter port number (1-65535)"
	ti.CharLimit = 5
	ti.Width = 40
	ti.Focus()

	return ProxytunnelPortModel{
		publicID:  publicID,
		textInput: ti,
		width:     100,
		lg:        lipgloss.DefaultRenderer(),
		err:       "",
	}
}

func (m ProxytunnelPortModel) Init() tea.Cmd {
	return textinput.Blink
}

func (m ProxytunnelPortModel) Update(msg tea.Msg) (ProxytunnelPortModel, tea.Cmd) {
	var cmd tea.Cmd

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
			// Validate and submit port
			portStr := strings.TrimSpace(m.textInput.Value())
			port, err := strconv.Atoi(portStr)
			if err != nil || port < 1 || port > 65535 {
				// Invalid port, show error
				m.err = "Invalid port (must be 1-65535)"
				return m, nil
			}
			// Valid port, open tunnel
			return m, func() tea.Msg {
				return openTunnelMsg{
					publicID:   m.publicID,
					remotePort: port,
				}
			}
		default:
			// Clear error on new input
			m.err = ""
		}
	}

	// Update text input
	m.textInput, cmd = m.textInput.Update(msg)
	return m, cmd
}

func (m ProxytunnelPortModel) View() string {
	headerStyle := m.lg.NewStyle().
		Foreground(lipgloss.AdaptiveColor{Light: "#5A56E0", Dark: "#7571F9"}).
		Bold(true).
		Padding(0, 1, 0, 2)

	header := headerStyle.Render("Enter Remote Port for Proxytunnel")

	titleStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("205")).
		Bold(true).
		MarginTop(1).
		MarginLeft(2)

	inputStyle := m.lg.NewStyle().
		MarginLeft(2).
		MarginTop(1)

	helpStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("240")).
		MarginTop(2).
		MarginLeft(2)

	errorStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("196")).
		MarginLeft(2).
		MarginTop(1)

	body := titleStyle.Render("Remote port:") + "\n" +
		inputStyle.Render(m.textInput.View())

	if m.err != "" {
		body += "\n" + errorStyle.Render("⚠ "+m.err)
	}

	body += "\n" + helpStyle.Render("enter: open tunnel • esc: back to VM info • ctrl+c: quit")

	return components.RenderHeader() + "\n" + header + "\n" + body
}
