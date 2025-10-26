package main

import (
	"fmt"
	"plato-sdk/cmd/plato/internal/ui/components"
	"plato-sdk/cmd/plato/internal/utils"
	"strconv"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type DBEntryModel struct {
	service    string
	inputs     []textinput.Model
	focusIndex int
	width      int
	lg         *lipgloss.Renderer
	err        string
}

type dbConfigEnteredMsg struct {
	service string
	config  utils.DBConfig
}

func NewDBEntryModel(service string) DBEntryModel {
	inputs := make([]textinput.Model, 5)

	// DB Type
	inputs[0] = textinput.New()
	inputs[0].Placeholder = "postgresql or mysql"
	inputs[0].Focus()
	inputs[0].CharLimit = 20
	inputs[0].Width = 40

	// User
	inputs[1] = textinput.New()
	inputs[1].Placeholder = "database username"
	inputs[1].CharLimit = 50
	inputs[1].Width = 40

	// Password
	inputs[2] = textinput.New()
	inputs[2].Placeholder = "database password"
	inputs[2].CharLimit = 100
	inputs[2].Width = 40
	inputs[2].EchoMode = textinput.EchoPassword
	inputs[2].EchoCharacter = '•'

	// Port
	inputs[3] = textinput.New()
	inputs[3].Placeholder = "5432 or 3306"
	inputs[3].CharLimit = 5
	inputs[3].Width = 40

	// Database names (comma-separated)
	inputs[4] = textinput.New()
	inputs[4].Placeholder = "postgres,mydb (comma-separated)"
	inputs[4].CharLimit = 200
	inputs[4].Width = 40

	return DBEntryModel{
		service:    service,
		inputs:     inputs,
		focusIndex: 0,
		width:      100,
		lg:         lipgloss.DefaultRenderer(),
		err:        "",
	}
}

func (m DBEntryModel) Init() tea.Cmd {
	return textinput.Blink
}

func (m DBEntryModel) Update(msg tea.Msg) (DBEntryModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "esc":
			// Skip DB cleanup and go back to VM info
			return m, func() tea.Msg {
				return NavigateMsg{view: ViewVMInfo}
			}
		case "tab", "shift+tab", "enter", "up", "down":
			s := msg.String()

			// Enter on last field = submit
			if s == "enter" && m.focusIndex == len(m.inputs)-1 {
				// Validate and submit
				dbType := strings.TrimSpace(strings.ToLower(m.inputs[0].Value()))
				user := strings.TrimSpace(m.inputs[1].Value())
				password := m.inputs[2].Value()
				portStr := strings.TrimSpace(m.inputs[3].Value())
				databasesStr := strings.TrimSpace(m.inputs[4].Value())

				// Validate
				if dbType != "postgresql" && dbType != "mysql" {
					m.err = "DB type must be 'postgresql' or 'mysql'"
					return m, nil
				}
				if user == "" {
					m.err = "Username is required"
					return m, nil
				}
				port, err := strconv.Atoi(portStr)
				if err != nil || port < 1 || port > 65535 {
					m.err = "Invalid port number"
					return m, nil
				}
				if databasesStr == "" {
					m.err = "At least one database name is required"
					return m, nil
				}

				// Parse databases
				databases := []string{}
				for _, db := range strings.Split(databasesStr, ",") {
					db = strings.TrimSpace(db)
					if db != "" {
						databases = append(databases, db)
					}
				}

				if len(databases) == 0 {
					m.err = "At least one database name is required"
					return m, nil
				}

				// Create config
				config := utils.DBConfig{
					DBType:    dbType,
					User:      user,
					Password:  password,
					DestPort:  port,
					Databases: databases,
				}

				// Save and return
				if err := utils.SaveCustomDBConfig(m.service, config); err != nil {
					m.err = fmt.Sprintf("Failed to save config: %v", err)
					return m, nil
				}

				return m, func() tea.Msg {
					return dbConfigEnteredMsg{
						service: m.service,
						config:  config,
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

func (m *DBEntryModel) updateInputs(msg tea.Msg) tea.Cmd {
	cmds := make([]tea.Cmd, len(m.inputs))
	for i := range m.inputs {
		m.inputs[i], cmds[i] = m.inputs[i].Update(msg)
	}
	return tea.Batch(cmds...)
}

func (m DBEntryModel) View() string {
	headerStyle := m.lg.NewStyle().
		Foreground(lipgloss.AdaptiveColor{Light: "#5A56E0", Dark: "#7571F9"}).
		Bold(true).
		Padding(0, 1, 0, 2)

	header := headerStyle.Render(fmt.Sprintf("Enter Database Info for '%s'", m.service))

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
		"Database Type:",
		"Username:",
		"Password:",
		"Port:",
		"Database Names:",
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
	body.WriteString(helpStyle.Render("tab/shift+tab: navigate • enter: submit • esc: skip DB cleanup"))

	return components.RenderHeader() + "\n" + header + "\n" + body.String()
}
