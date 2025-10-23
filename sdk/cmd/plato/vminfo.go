package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	plato "plato-sdk"
	"plato-sdk/models"

	"github.com/charmbracelet/bubbles/list"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/lipgloss"
)

const vmInfoMaxWidth = 120

var (
	vmInfoIndigo = lipgloss.AdaptiveColor{Light: "#5A56E0", Dark: "#7571F9"}
	vmInfoGreen  = lipgloss.AdaptiveColor{Light: "#02BA84", Dark: "#02BF87"}
)

type VMInfoModel struct {
	client         *plato.PlatoClient
	sandbox        *models.Sandbox
	dataset        string
	lg             *lipgloss.Renderer
	width          int
	actionList     list.Model
	settingUp      bool
	setupComplete  bool
	spinner        spinner.Model
	statusMessages []string
	statusChan     chan string
	sshURL         string
	sshHost        string
	viewport       viewport.Model
	viewportReady  bool
	heartbeatStop  chan struct{}
}

type vmAction struct {
	title       string
	description string
}

func (v vmAction) Title() string       { return v.title }
func (v vmAction) Description() string { return v.description }
func (v vmAction) FilterValue() string { return v.title }

type sandboxSetupMsg struct {
	sshURL string
	err    error
}

func NewVMInfoModel(client *plato.PlatoClient, sandbox *models.Sandbox, dataset string) VMInfoModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	items := []list.Item{
		vmAction{title: "Start Plato Worker", description: "Start the Plato worker process"},
		vmAction{title: "Connect via SSH", description: "Open SSH connection to VM"},
		vmAction{title: "Snapshot VM", description: "Create snapshot of current VM state"},
		vmAction{title: "Close VM", description: "Shutdown and cleanup VM"},
	}

	l := list.New(items, list.NewDefaultDelegate(), 40, 18)
	l.Title = "Actions"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(false)
	l.SetShowHelp(false)
	l.SetShowPagination(false)

	// Initialize viewport immediately with wider width
	vp := viewport.New(100, 18)
	vp.Style = lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(vmInfoIndigo).
		PaddingLeft(1)

	return VMInfoModel{
		client:         client,
		sandbox:        sandbox,
		dataset:        dataset,
		lg:             lipgloss.DefaultRenderer(),
		width:          vmInfoMaxWidth,
		actionList:     l,
		settingUp:      false,
		setupComplete:  false,
		spinner:        s,
		statusMessages: []string{},
		viewport:       vp,
		viewportReady:  true,
		heartbeatStop:  make(chan struct{}),
	}
}

func setupSandbox(client *plato.PlatoClient, sandbox *models.Sandbox, dataset string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		statusChan <- "Setting up sandbox environment..."

		statusChan <- "Calling setup-sandbox API..."

		// Call the setup-sandbox API
		// TODO: Need to get the actual config here - for now using empty config
		emptyConfig := models.SimConfigDataset{}
		correlationID, err := client.Sandbox.SetupSandbox(ctx, sandbox.PublicID, emptyConfig, dataset)
		if err != nil {
			statusChan <- fmt.Sprintf("Setup failed: %v", err)
			close(statusChan)
			return sandboxSetupMsg{
				sshURL: "",
				err:    err,
			}
		}

		statusChan <- "Monitoring setup operation..."

		// Monitor the setup operation via SSE using the returned correlation_id
		err = client.Sandbox.MonitorOperation(ctx, correlationID, 20*time.Minute)
		if err != nil {
			statusChan <- fmt.Sprintf("Setup monitoring failed: %v", err)
			close(statusChan)
			return sandboxSetupMsg{
				sshURL: "",
				err:    fmt.Errorf("setup monitoring failed: %w", err),
			}
		}

		// Generate SSH connection info
		sshURL := fmt.Sprintf("root@%s", sandbox.JobGroupID)

		statusChan <- "Sandbox setup complete!"
		close(statusChan)

		return sandboxSetupMsg{
			sshURL: sshURL,
			err:    nil,
		}
	}
}

func (m VMInfoModel) startHeartbeat() {
	// Start heartbeat goroutine
	go func() {
		ticker := time.NewTicker(30 * time.Second) // Send heartbeat every 30 seconds
		defer ticker.Stop()

		ctx := context.Background()

		// Send initial heartbeat immediately
		_ = m.client.Sandbox.SendHeartbeat(ctx, m.sandbox.JobGroupID)

		for {
			select {
			case <-ticker.C:
				// Send heartbeat
				if err := m.client.Sandbox.SendHeartbeat(ctx, m.sandbox.JobGroupID); err != nil {
					// Silently fail - don't interrupt the UI
					continue
				}
			case <-m.heartbeatStop:
				// Stop the heartbeat
				return
			}
		}
	}()
}

func (m VMInfoModel) Init() tea.Cmd {
	// Setup should already be done when we reach this view
	// Start sending heartbeats to keep the VM alive
	m.startHeartbeat()
	return nil
}

func (m VMInfoModel) Update(msg tea.Msg) (VMInfoModel, tea.Cmd) {
	switch msg := msg.(type) {
	case statusUpdateMsg:
		if msg.message != "" {
			m.statusMessages = append(m.statusMessages, msg.message)
		}
		if m.settingUp && m.statusChan != nil {
			return m, waitForStatusUpdates(m.statusChan)
		}
		return m, nil

	case sandboxSetupMsg:
		m.settingUp = false
		m.setupComplete = true
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Setup failed: %v", msg.err))
		} else {
			m.sshURL = msg.sshURL
			m.statusMessages = append(m.statusMessages, "✓ Sandbox ready!")
		}
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.WindowSizeMsg:
		m.width = msg.Width
		if m.width > vmInfoMaxWidth {
			m.width = vmInfoMaxWidth
		}
		// Viewport is already initialized, just update dimensions if needed
		m.viewport.Width = 100
		m.viewport.Height = 18

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "enter":
			if !m.settingUp {
				selectedItem := m.actionList.SelectedItem()
				if selectedItem != nil {
					action := selectedItem.(vmAction)
					return m.handleAction(action)
				}
			}
		}
	}

	// Update action list and viewport if not setting up
	if !m.settingUp {
		var cmds []tea.Cmd
		var cmd tea.Cmd

		m.actionList, cmd = m.actionList.Update(msg)
		cmds = append(cmds, cmd)

		m.viewport, cmd = m.viewport.Update(msg)
		cmds = append(cmds, cmd)

		return m, tea.Batch(cmds...)
	}

	return m, nil
}

func (m VMInfoModel) renderVMInfoMarkdown() string {
	var md strings.Builder

	md.WriteString("## VM Information\n\n")
	md.WriteString(fmt.Sprintf("**Job ID:** `%s`\n\n", m.sandbox.PublicID))
	md.WriteString(fmt.Sprintf("**Dataset:** `%s`\n\n", m.dataset))
	md.WriteString(fmt.Sprintf("**URL:** %s\n\n", m.sandbox.URL))

	if m.setupComplete {
		md.WriteString("---\n\n")
		md.WriteString("## Connection Info\n\n")
		if m.sshHost != "" {
			md.WriteString(fmt.Sprintf("**SSH:** `ssh %s`\n\n", m.sshHost))
		} else {
			md.WriteString(fmt.Sprintf("**SSH:** `%s`\n\n", m.sshURL))
		}
	}

	// Render markdown with glamour
	renderer, err := glamour.NewTermRenderer(
		glamour.WithAutoStyle(),
		glamour.WithWordWrap(96), // Account for padding and borders (100 - 4)
	)
	if err != nil {
		return md.String()
	}

	rendered, err := renderer.Render(md.String())
	if err != nil {
		return md.String()
	}

	return rendered
}

func (m VMInfoModel) handleAction(action vmAction) (VMInfoModel, tea.Cmd) {
	switch action.title {
	case "Start Plato Worker":
		// TODO: Implement Plato worker start
		m.statusMessages = append(m.statusMessages, "Starting Plato worker not implemented yet")
	case "Connect via SSH":
		// TODO: Implement SSH connection
		m.statusMessages = append(m.statusMessages, "SSH connection not implemented yet")
	case "Snapshot VM":
		// TODO: Implement snapshot
		m.statusMessages = append(m.statusMessages, "Snapshot not implemented yet")
	case "Close VM":
		// Stop heartbeat goroutine
		close(m.heartbeatStop)
		// Cleanup SSH config entry if exists
		if m.sshHost != "" {
			_ = cleanupSSHConfig(m.sshHost)
		}
		// TODO: Implement VM cleanup API call
		return m, func() tea.Msg {
			return NavigateMsg{view: ViewMainMenu}
		}
	}
	return m, nil
}

func (m VMInfoModel) View() string {
	headerStyle := m.lg.NewStyle().
		Foreground(vmInfoIndigo).
		Bold(true).
		Padding(0, 1, 0, 2)

	header := lipgloss.PlaceHorizontal(
		m.width,
		lipgloss.Left,
		headerStyle.Render("Virtual Machine Management"),
		lipgloss.WithWhitespaceChars("/"),
		lipgloss.WithWhitespaceForeground(vmInfoIndigo),
	)

	// If setting up, show spinner and status
	if m.settingUp {
		statusMsgStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#CCCCCC")).
			MarginLeft(2)

		prevStatusStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#888888")).
			MarginLeft(4)

		var statusContent string
		for i, msg := range m.statusMessages {
			if i == len(m.statusMessages)-1 {
				statusContent += statusMsgStyle.Render(fmt.Sprintf("  %s %s", m.spinner.View(), msg)) + "\n"
			} else {
				statusContent += prevStatusStyle.Render(fmt.Sprintf("  ✓ %s", msg)) + "\n"
			}
		}

		body := lipgloss.NewStyle().MarginTop(1).Render(statusContent)
		return RenderHeader() + "\n" + header + "\n" + body
	}

	// Build VM info panel (right side) using glamour and viewport
	renderedMarkdown := m.renderVMInfoMarkdown()
	m.viewport.SetContent(renderedMarkdown)
	vmInfoPanel := m.viewport.View()

	// Actions panel (left side)
	actionsPanel := m.lg.NewStyle().
		Margin(1, 4, 1, 0).
		Render(m.actionList.View())

	body := lipgloss.JoinHorizontal(lipgloss.Left, actionsPanel, vmInfoPanel)

	helpStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("240")).
		MarginTop(1).
		MarginLeft(2)

	footer := helpStyle.Render("enter: select action • ctrl+c: force quit")

	return RenderHeader() + "\n" + header + "\n" + body + "\n" + footer
}
