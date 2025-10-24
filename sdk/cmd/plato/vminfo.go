package main

import (
	"context"
	"fmt"
	"os"
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

// logErrorToFile writes an error message to a log file with timestamp
func logErrorToFile(filename, message string) error {
	f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	logMessage := fmt.Sprintf("[%s] %s\n", timestamp, message)
	_, err = f.WriteString(logMessage)
	return err
}

type VMInfoModel struct {
	client            *plato.PlatoClient
	sandbox           *models.Sandbox
	dataset           string
	lg                *lipgloss.Renderer
	width             int
	actionList        list.Model
	settingUp         bool
	setupComplete     bool
	spinner           spinner.Model
	statusMessages    []string
	statusChan        chan string
	sshURL            string
	sshHost           string
	viewport          viewport.Model
	viewportReady     bool
	heartbeatStop     chan struct{}
	fromExistingSim   bool
	rootPasswordSetup bool
	config            *models.PlatoConfig
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

type rootPasswordSetupMsg struct {
	err error
}

type snapshotCreatedMsg struct {
	err      error
	response *models.CreateSnapshotResponse
}

func NewVMInfoModel(client *plato.PlatoClient, sandbox *models.Sandbox, dataset string, fromExistingSim bool) VMInfoModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	items := []list.Item{
		vmAction{title: "Start Plato Worker", description: "Start the Plato worker process"},
		vmAction{title: "Connect via SSH", description: "Open SSH connection to VM"},
	}

	// Add "Setup Root SSH" action if launched from existing simulator
	if fromExistingSim {
		items = append(items, vmAction{title: "Setup Root SSH", description: "Configure root password for SSH access"})
	}

	items = append(items,
		vmAction{title: "Snapshot VM", description: "Create snapshot of current VM state"},
		vmAction{title: "Close VM", description: "Shutdown and cleanup VM"},
	)

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
		client:            client,
		sandbox:           sandbox,
		dataset:           dataset,
		lg:                lipgloss.DefaultRenderer(),
		width:             vmInfoMaxWidth,
		actionList:        l,
		settingUp:         false,
		setupComplete:     false,
		spinner:           s,
		statusMessages:    []string{},
		viewport:          vp,
		viewportReady:     true,
		heartbeatStop:     make(chan struct{}),
		fromExistingSim:   fromExistingSim,
		rootPasswordSetup: false,
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

	case rootPasswordSetupMsg:
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Root password setup failed: %v", msg.err))
		} else {
			m.rootPasswordSetup = true
			// Update SSH config with password and change user to root
			if m.sshHost != "" {
				// First, update the username to root
				if err := updateSSHConfigUser(m.sshHost, "root"); err != nil {
					m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to update SSH config user: %v", err))
				} else if err := updateSSHConfigPassword(m.sshHost, "password"); err != nil {
					m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to update SSH config password: %v", err))
				} else {
					m.statusMessages = append(m.statusMessages, "✓ Root SSH password configured!")
				}
			} else {
				m.statusMessages = append(m.statusMessages, "✓ Root password set!")
			}
		}
		// Update viewport content and scroll to bottom
		renderedMarkdown := m.renderVMInfoMarkdown()
		m.viewport.SetContent(renderedMarkdown)
		m.viewport.GotoBottom()
		return m, nil

	case snapshotCreatedMsg:
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Snapshot failed: %v", msg.err))
		} else if msg.response != nil {
			m.statusMessages = append(m.statusMessages, "✓ Snapshot created successfully!")
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Artifact ID: %s", msg.response.ArtifactID))
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Status: %s", msg.response.Status))
			if msg.response.S3URI != "" {
				m.statusMessages = append(m.statusMessages, fmt.Sprintf("   S3 URI: %s", msg.response.S3URI))
			}
		}
		// Update viewport content and scroll to bottom
		renderedMarkdown := m.renderVMInfoMarkdown()
		m.viewport.SetContent(renderedMarkdown)
		m.viewport.GotoBottom()
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

	// Show recent status messages if any
	if len(m.statusMessages) > 0 {
		md.WriteString("---\n\n")
		md.WriteString("## Status\n\n")
		// Show last 5 messages
		start := 0
		if len(m.statusMessages) > 5 {
			start = len(m.statusMessages) - 5
		}
		for _, msg := range m.statusMessages[start:] {
			md.WriteString(fmt.Sprintf("- %s\n", msg))
		}
		md.WriteString("\n")
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

func setupRootPassword(client *plato.PlatoClient, publicID string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		err := client.Sandbox.SetupRootPassword(ctx, publicID, "password")
		if err != nil {
			return rootPasswordSetupMsg{err: err}
		}

		return rootPasswordSetupMsg{err: nil}
	}
}

func createSnapshot(client *plato.PlatoClient, publicID string, service string, dataset *string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		req := models.CreateSnapshotRequest{
			Service: service,
			Dataset: dataset,
		}

		resp, err := client.Sandbox.CreateSnapshot(ctx, publicID, req)
		if err != nil {
			// Log error to file
			logErr := logErrorToFile("plato_error.log", fmt.Sprintf("API: CreateSnapshot failed for %s: %v", publicID, err))
			if logErr != nil {
				fmt.Printf("Failed to write error log: %v\n", logErr)
			}
			return snapshotCreatedMsg{err: err, response: nil}
		}

		return snapshotCreatedMsg{err: nil, response: resp}
	}
}

func (m VMInfoModel) handleAction(action vmAction) (VMInfoModel, tea.Cmd) {
	switch action.title {
	case "Start Plato Worker":
		// TODO: Implement Plato worker start
		m.statusMessages = append(m.statusMessages, "Starting Plato worker not implemented yet")
	case "Connect via SSH":
		// TODO: Implement SSH connection
		m.statusMessages = append(m.statusMessages, "SSH connection not implemented yet")
	case "Setup Root SSH":
		if m.rootPasswordSetup {
			m.statusMessages = append(m.statusMessages, "Root password already configured")
			return m, nil
		}
		m.statusMessages = append(m.statusMessages, "Setting up root SSH password...")
		return m, setupRootPassword(m.client, m.sandbox.PublicID)
	case "Snapshot VM":
		m.statusMessages = append(m.statusMessages, "Creating snapshot...")

		// Load the config to get service and dataset
		config, err := LoadPlatoConfig()
		if err != nil {
			errMsg := fmt.Sprintf("❌ Failed to load plato-config.yml: %v", err)
			m.statusMessages = append(m.statusMessages, errMsg)
			logErrorToFile("plato_error.log", errMsg)
			return m, nil
		}

		// Get service from config
		service := config.Service
		if service == "" {
			errMsg := "❌ Service not specified in plato-config.yml"
			m.statusMessages = append(m.statusMessages, errMsg)
			logErrorToFile("plato_error.log", errMsg)
			return m, nil
		}

		// Use the dataset from the model
		datasetPtr := &m.dataset

		return m, createSnapshot(m.client, m.sandbox.PublicID, service, datasetPtr)
	case "Close VM":
		// Stop heartbeat goroutine
		close(m.heartbeatStop)
		// Cleanup SSH config entry if exists
		if m.sshHost != "" {
			_ = cleanupSSHConfig(m.sshHost)
		}
		// Call VM cleanup API
		return m, func() tea.Msg {
			ctx := context.Background()
			if err := m.client.Sandbox.DeleteVM(ctx, m.sandbox.PublicID); err != nil {
				// Log error but still navigate away
				fmt.Printf("Warning: failed to delete VM: %v\n", err)
			}
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
