// Package main provides the VM information and management view for the Plato CLI.
//
// This file implements the VMInfoModel which displays detailed information about
// a running VM sandbox including SSH connection details, available actions like
// creating snapshots, setting up root passwords, starting workers, opening proxy
// tunnels, and managing the VM lifecycle. It provides an interactive menu for
// performing various operations on the VM.
package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	plato "plato-sdk"
	"plato-sdk/cmd/plato/internal/ui/components"
	"plato-sdk/cmd/plato/internal/utils"
	"plato-sdk/models"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/list"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
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

type proxytunnelMapping struct {
	localPort  int
	remotePort int
}

type VMInfoModel struct {
	client               *plato.PlatoClient
	sandbox              *models.Sandbox
	dataset              string
	artifactID           *string
	version              *string
	lg                   *lipgloss.Renderer
	width                int
	actionList           list.Model
	settingUp            bool
	setupComplete        bool
	spinner              spinner.Model
	statusMessages       []string
	statusChan           chan string
	sshURL               string
	sshHost              string
	sshConfigPath        string
	sshPrivateKeyPath    string
	viewport             viewport.Model
	viewportReady        bool
	heartbeatStop        chan struct{}
	heartbeatStopped     bool
	fromExistingSim      bool
	rootPasswordSetup    bool
	proxytunnelProcesses []*exec.Cmd
	proxytunnelMappings  []proxytunnelMapping
	config               *models.PlatoConfig
	lastPushedBranch     string // Tracks the last branch pushed to hub
	cachedCloneCmd       string // Cached clone command to avoid repeated API calls
	hubRepoURL           string // Cached hub repository URL
	infoPanelFocused     bool   // Whether the info panel has focus (vs actions list)
	runningCommand       bool   // Whether a command is currently running
	ecrAuthenticated     bool   // Whether ECR authentication has been completed
}

type vmAction struct {
	title       string
	description string
}

func (v vmAction) Title() string       { return v.title }
func (v vmAction) Description() string { return v.description }
func (v vmAction) FilterValue() string { return v.title }

type sandboxSetupMsg struct {
	sshURL        string
	sshHost       string
	sshConfigPath string
	err           error
}

type rootPasswordSetupMsg struct {
	err error
}

type snapshotCreatedMsg struct {
	err      error
	response *models.CreateSnapshotResponse
}

type proxytunnelOpenedMsg struct {
	localPort  int
	remotePort int
	cmd        *exec.Cmd
	err        error
}

type workerStartedMsg struct {
	err      error
	response *models.StartWorkerResponse
}

type cursorOpenedMsg struct {
	err error
}

type hubPushMsg struct {
	err        error
	repoURL    string
	cloneCmd   string
	branchName string
}

type serviceStartedMsg struct {
	err          error
	repoURL      string
	branchName   string
	servicesInfo []string
}

type ecrAuthenticatedMsg struct {
	err error
}

type triggerECRAuthMsg struct{}

type hubRepoURLMsg struct {
	url string
}

func NewVMInfoModel(client *plato.PlatoClient, sandbox *models.Sandbox, dataset string, fromExistingSim bool, artifactID *string, version *string) VMInfoModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	items := []list.Item{
		vmAction{title: "Start Service", description: "Start the service defined in plato-config.yml"},
		vmAction{title: "Start Plato Worker", description: "Start the Plato worker process"},
		vmAction{title: "Connect to Cursor/VSCode", description: "Open Cursor/VSCode editor connected to VM via SSH"},
		vmAction{title: "Snapshot VM", description: "Create snapshot of current VM state"},
		vmAction{title: "Advanced", description: "Advanced VM management options"},
		vmAction{title: "Close VM", description: "Shutdown and cleanup VM"},
	}

	l := list.New(items, list.NewDefaultDelegate(), 40, 24)
	l.Title = "Actions"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(false)
	l.SetShowHelp(false)
	l.SetShowPagination(false)

	// Initialize viewport immediately with wider width
	vp := viewport.New(100, 24)
	vp.Style = lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(vmInfoIndigo).
		PaddingLeft(1)

	// Try to load plato-config.yml
	var config *models.PlatoConfig
	if cfg, err := LoadPlatoConfig(); err == nil {
		config = cfg
	}

	return VMInfoModel{
		client:               client,
		sandbox:              sandbox,
		dataset:              dataset,
		artifactID:           artifactID,
		version:              version,
		lg:                   lipgloss.DefaultRenderer(),
		width:                vmInfoMaxWidth,
		actionList:           l,
		settingUp:            false,
		setupComplete:        false,
		spinner:              s,
		statusMessages:       []string{},
		viewport:             vp,
		viewportReady:        true,
		heartbeatStop:        make(chan struct{}),
		heartbeatStopped:     false,
		fromExistingSim:      fromExistingSim,
		rootPasswordSetup:    false,
		proxytunnelProcesses: []*exec.Cmd{},
		proxytunnelMappings:  []proxytunnelMapping{},
		config:               config,
		infoPanelFocused:     false, // Start with actions list focused
		ecrAuthenticated:     false,
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

// wrapText wraps text to the specified width, breaking on word boundaries
func wrapText(text string, width int) string {
	if width <= 0 {
		return text
	}

	var result strings.Builder
	var currentLine strings.Builder
	currentLength := 0

	words := strings.Fields(text)
	for i, word := range words {
		wordLen := len(word)

		if currentLength == 0 {
			// First word on the line
			currentLine.WriteString(word)
			currentLength = wordLen
		} else if currentLength+1+wordLen <= width {
			// Word fits on current line
			currentLine.WriteString(" " + word)
			currentLength += 1 + wordLen
		} else {
			// Word doesn't fit, start new line
			result.WriteString(currentLine.String() + "\n")
			currentLine.Reset()
			currentLine.WriteString(word)
			currentLength = wordLen
		}

		// If this is the last word, add remaining content
		if i == len(words)-1 {
			result.WriteString(currentLine.String())
		}
	}

	return result.String()
}

func (m VMInfoModel) Init() tea.Cmd {
	// Setup should already be done when we reach this view
	// Start sending heartbeats to keep the VM alive
	m.startHeartbeat()

	var cmds []tea.Cmd

	// Automatically authenticate with ECR if setup is complete and not already authenticated
	// This handles the case where the VM is initialized via navigateToVMInfoMsg (bypassing sandboxSetupMsg)
	if m.setupComplete && !m.ecrAuthenticated && m.sshHost != "" && m.sshConfigPath != "" {
		cmds = append(cmds, func() tea.Msg {
			return triggerECRAuthMsg{}
		})
	}

	// Fetch hub repository URL in background if we have a config
	if m.config != nil && m.config.Service != "" {
		cmds = append(cmds, fetchHubRepoURL(m.client, m.config.Service))
	}

	if len(cmds) > 0 {
		return tea.Batch(cmds...)
	}

	return nil
}

func (m VMInfoModel) Update(msg tea.Msg) (VMInfoModel, tea.Cmd) {
	switch msg := msg.(type) {
	case statusUpdateMsg:
		if msg.message != "" {
			m.statusMessages = append(m.statusMessages, msg.message)
			// If this is a completion message, clear running state
			if strings.Contains(msg.message, "complete!") || strings.Contains(msg.message, "✓") {
				m.runningCommand = false
			}
			// Update viewport content to reflect new status
			m.viewport.SetContent(m.renderVMInfoMarkdown())
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
			return m, nil
		} else {
			m.sshURL = msg.sshURL
			m.sshHost = msg.sshHost
			m.sshConfigPath = msg.sshConfigPath
			m.statusMessages = append(m.statusMessages, "✓ Sandbox ready!")
			// Automatically authenticate with ECR for 2 hours (ECR tokens are valid for 12 hours by default)
			if !m.ecrAuthenticated && m.sshHost != "" && m.sshConfigPath != "" {
				m.statusMessages = append(m.statusMessages, "🔐 Authenticating Docker with AWS ECR...")
				m.runningCommand = true
				return m, tea.Batch(m.spinner.Tick, authenticateECR(m.sshHost, m.sshConfigPath))
			}
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case rootPasswordSetupMsg:
		utils.LogDebug("rootPasswordSetupMsg received, err: %v", msg.err)
		m.runningCommand = false
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Root password setup failed: %v", msg.err))
		} else {
			m.rootPasswordSetup = true
			// Update SSH config with password and change user to root
			if m.sshHost != "" && m.sshConfigPath != "" {
				// First, update the username to root in the per-VM SSH config file
				if err := utils.UpdateSSHConfigFileUser(m.sshConfigPath, m.sshHost, "root"); err != nil {
					m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to update SSH config user: %v", err))
				} else if err := utils.UpdateSSHConfigFilePassword(m.sshConfigPath, m.sshHost, "password"); err != nil {
					m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to update SSH config password: %v", err))
				} else {
					m.statusMessages = append(m.statusMessages, "✓ Root SSH password configured!")
				}
			} else {
				m.statusMessages = append(m.statusMessages, "✓ Root password set!")
			}
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case snapshotCreatedMsg:
		m.runningCommand = false
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Snapshot failed: %v", msg.err))
		} else if msg.response != nil {
			m.statusMessages = append(m.statusMessages, "✓ Snapshot created successfully!")
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Artifact ID: %s", msg.response.ArtifactID))
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Status: %s", msg.response.Status))
			if msg.response.GitHash != "" {
				m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Git Hash: %s", msg.response.GitHash))
			}
			if msg.response.S3URI != "" {
				m.statusMessages = append(m.statusMessages, fmt.Sprintf("   S3 URI: %s", msg.response.S3URI))
			}
			// Clear the last pushed branch and cached clone cmd since it's been merged
			m.lastPushedBranch = ""
			m.cachedCloneCmd = ""
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case workerStartedMsg:
		if msg.err != nil {
			m.runningCommand = false
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Worker start failed: %v", msg.err))
			// Update viewport content to reflect new status
			m.viewport.SetContent(m.renderVMInfoMarkdown())
		} else if msg.response != nil {
			m.statusMessages = append(m.statusMessages, "✓ Worker start initiated!")
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Status: %s", msg.response.Status))
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Monitoring progress via correlation ID: %s", msg.response.CorrelationID))
			// Update viewport content to reflect new status
			m.viewport.SetContent(m.renderVMInfoMarkdown())
			// Monitor the operation using SSE events
			return m, tea.Batch(
				m.spinner.Tick,
				func() tea.Msg {
					ctx := context.Background()
					err := m.client.Sandbox.MonitorOperation(ctx, msg.response.CorrelationID, 10*time.Minute)
					if err != nil {
						return workerStartedMsg{err: fmt.Errorf("worker setup failed: %w", err), response: nil}
					}
					// Success - add a final message
					return statusUpdateMsg{message: "✓ Worker setup complete!"}
				},
			)
		}
		return m, nil

	case hubPushMsg:
		m.runningCommand = false
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Push to hub failed: %v", msg.err))
		} else {
			m.lastPushedBranch = msg.branchName
			m.cachedCloneCmd = msg.cloneCmd // Cache the clone command
			m.statusMessages = append(m.statusMessages, "✓ Successfully pushed to Plato Hub!")
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Repository: %s", msg.repoURL))
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Branch: %s", msg.branchName))
			m.statusMessages = append(m.statusMessages, "")
			m.statusMessages = append(m.statusMessages, "💡 To pull code in your VM, SSH in and run:")
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   %s", msg.cloneCmd))
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case serviceStartedMsg:
		m.runningCommand = false
		if msg.err != nil {
			// Split error message into separate lines for better display
			errorMsg := msg.err.Error()
			m.statusMessages = append(m.statusMessages, "❌ Failed to start service")

			// Split by common delimiters and add each part as a separate message
			lines := strings.Split(errorMsg, "\n")
			for _, line := range lines {
				if strings.TrimSpace(line) != "" {
					m.statusMessages = append(m.statusMessages, "   "+strings.TrimSpace(line))
				}
			}
		} else {
			m.lastPushedBranch = msg.branchName
			m.statusMessages = append(m.statusMessages, "✓ Service started successfully!")
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Repository: %s", msg.repoURL))
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Branch: %s", msg.branchName))
			m.statusMessages = append(m.statusMessages, "")
			for _, info := range msg.servicesInfo {
				m.statusMessages = append(m.statusMessages, info)
			}
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case triggerECRAuthMsg:
		// Trigger ECR authentication
		m.statusMessages = append(m.statusMessages, "🔐 Authenticating Docker with AWS ECR...")
		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, authenticateECR(m.sshHost, m.sshConfigPath))

	case ecrAuthenticatedMsg:
		m.runningCommand = false
		if msg.err != nil {
			// Split error message into separate lines for better display
			errorMsg := msg.err.Error()
			m.statusMessages = append(m.statusMessages, "❌ ECR authentication failed")

			lines := strings.Split(errorMsg, "\n")
			for _, line := range lines {
				if strings.TrimSpace(line) != "" {
					m.statusMessages = append(m.statusMessages, "   "+strings.TrimSpace(line))
				}
			}
		} else {
			m.ecrAuthenticated = true
			m.statusMessages = append(m.statusMessages, "✓ Successfully authenticated Docker with AWS ECR (valid for 12 hours)")
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case hubRepoURLMsg:
		// Cache the hub repo URL for display
		m.hubRepoURL = msg.url
		// Update viewport content with new info
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case proxytunnelOpenedMsg:
		utils.LogDebug("proxytunnelOpenedMsg received, localPort=%d, remotePort=%d, err=%v", msg.localPort, msg.remotePort, msg.err)
		m.runningCommand = false
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to open proxytunnel: %v", msg.err))
		} else {
			m.proxytunnelProcesses = append(m.proxytunnelProcesses, msg.cmd)
			m.proxytunnelMappings = append(m.proxytunnelMappings, proxytunnelMapping{
				localPort:  msg.localPort,
				remotePort: msg.remotePort,
			})
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("✓ Proxytunnel: localhost:%d → remote:%d", msg.localPort, msg.remotePort))
			utils.LogDebug("Added to lists, now have %d processes and %d mappings", len(m.proxytunnelProcesses), len(m.proxytunnelMappings))
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
		return m, nil

	case cursorOpenedMsg:
		utils.LogDebug("cursorOpenedMsg received, err=%v", msg.err)
		m.runningCommand = false
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to open Cursor: %v", msg.err))
		} else {
			m.statusMessages = append(m.statusMessages, "✓ Cursor opened successfully")
		}
		// Update viewport content to reflect new status
		m.viewport.SetContent(m.renderVMInfoMarkdown())
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
		m.viewport.Height = 24
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "i":
			// Toggle focus between actions list and info panel
			m.infoPanelFocused = !m.infoPanelFocused
			// Update viewport content when focusing
			if m.infoPanelFocused {
				renderedMarkdown := m.renderVMInfoMarkdown()
				m.viewport.SetContent(renderedMarkdown)
			}
			return m, nil
		case "enter":
			if !m.settingUp && !m.runningCommand {
				selectedItem := m.actionList.SelectedItem()
				if selectedItem != nil {
					action := selectedItem.(vmAction)
					return m.handleAction(action)
				}
			}
		}
	}

	// Update action list and viewport if not setting up or running command
	if !m.settingUp && !m.runningCommand {
		var cmds []tea.Cmd
		var cmd tea.Cmd

		// Only update the focused component
		// Actions list or info panel based on focus
		if !m.infoPanelFocused {
			m.actionList, cmd = m.actionList.Update(msg)
			cmds = append(cmds, cmd)
		} else {
			// When info panel is focused, viewport handles scrolling
			m.viewport, cmd = m.viewport.Update(msg)
			cmds = append(cmds, cmd)
		}

		return m, tea.Batch(cmds...)
	}

	return m, nil
}

func (m VMInfoModel) renderVMInfoMarkdown() string {
	var output strings.Builder

	// VM Information section
	output.WriteString("VM INFORMATION\n")
	output.WriteString(strings.Repeat("─", 50) + "\n\n")
	output.WriteString(fmt.Sprintf("Job ID:   %s\n", m.sandbox.PublicID))
	output.WriteString(fmt.Sprintf("Dataset:  %s\n", m.dataset))
	if m.artifactID != nil {
		output.WriteString(fmt.Sprintf("Artifact: %s\n", *m.artifactID))
	}
	if m.version != nil {
		output.WriteString(fmt.Sprintf("Version:  %s\n", *m.version))
	}
	output.WriteString(fmt.Sprintf("URL:      %s\n", getSandboxPublicURL(m.client, m.sandbox)))

	// Show hub.plato.so repository link if we have it cached
	if m.hubRepoURL != "" {
		output.WriteString(fmt.Sprintf("Hub Repo: %s\n", m.hubRepoURL))
	}

	if m.setupComplete {
		output.WriteString("\n" + strings.Repeat("─", 50) + "\n\n")
		output.WriteString("CONNECTION INFO\n\n")
		if m.sshHost != "" && m.sshConfigPath != "" {
			output.WriteString(fmt.Sprintf("SSH:  ssh -F %s %s\n", m.sshConfigPath, m.sshHost))
		} else if m.sshHost != "" {
			output.WriteString(fmt.Sprintf("SSH:  ssh %s\n", m.sshHost))
		} else {
			output.WriteString(fmt.Sprintf("SSH:  %s\n", m.sshURL))
		}

		// Show active proxytunnel mappings
		if len(m.proxytunnelMappings) > 0 {
			output.WriteString("\nActive Proxytunnels:\n")
			for _, mapping := range m.proxytunnelMappings {
				output.WriteString(fmt.Sprintf("  • localhost:%d → remote:%d\n", mapping.localPort, mapping.remotePort))
			}
		}

		// Show hub branch info if available (use cached clone command)
		if m.lastPushedBranch != "" {
			output.WriteString("\n" + strings.Repeat("─", 50) + "\n\n")
			output.WriteString("HUB BRANCH\n\n")
			output.WriteString(fmt.Sprintf("Last Pushed Branch:  %s\n", m.lastPushedBranch))

			// Use cached clone command if available
			if m.cachedCloneCmd != "" {
				output.WriteString("\nClone Command (with auth):\n")
				output.WriteString(fmt.Sprintf("  %s\n", m.cachedCloneCmd))
				output.WriteString("\nThis branch will be merged into main when you snapshot.\n")
			}
		}
	}

	// Show recent status messages if any
	if len(m.statusMessages) > 0 {
		output.WriteString("\n" + strings.Repeat("─", 50) + "\n\n")
		output.WriteString("STATUS\n\n")
		// Show last 10 messages
		start := 0
		if len(m.statusMessages) > 10 {
			start = len(m.statusMessages) - 10
		}

		// Calculate wrap width based on viewport width (leave room for padding and scrollbar)
		wrapWidth := m.viewport.Width - 6
		if wrapWidth < 40 {
			wrapWidth = 40 // Minimum width
		}

		for _, msg := range m.statusMessages[start:] {
			// Wrap long messages for better readability
			wrapped := wrapText(msg, wrapWidth)
			lines := strings.Split(wrapped, "\n")
			for i, line := range lines {
				if i == 0 {
					output.WriteString(fmt.Sprintf("  %s\n", line))
				} else {
					// Indent continuation lines
					output.WriteString(fmt.Sprintf("    %s\n", line))
				}
			}
		}
	}

	return output.String()
}

func createSnapshotWithCleanup(client *plato.PlatoClient, publicID, jobGroupID, service string, dataset *string, branchName string) tea.Cmd {
	return func() tea.Msg {
		// Step 1: Perform pre-snapshot cleanup
		datasetName := "base"
		if dataset != nil {
			datasetName = *dataset
		}
		utils.LogDebug("Starting pre-snapshot cleanup for service: %s, dataset: %s", service, datasetName)
		needsDBConfig, err := utils.PreSnapshotCleanup(client, publicID, jobGroupID, service, datasetName)
		if err != nil {
			utils.LogDebug("Pre-snapshot cleanup failed: %v", err)
			// Don't fail the snapshot if cleanup fails, just log it
		}
		if needsDBConfig {
			// This shouldn't happen here since we check before calling this function
			utils.LogDebug("Warning: DB config needed but not provided")
		}

		// Step 2: Create the snapshot
		// Use a timeout context to prevent hanging (snapshots can take a while)
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		var gitHash *string

		// If a branch was pushed, merge it to main and get the commit hash
		if branchName != "" {
			hash, err := mergeHubBranchToMain(client, service, branchName)
			if err != nil {
				logErr := logErrorToFile("plato_error.log", fmt.Sprintf("Failed to merge branch to main: %v", err))
				if logErr != nil {
					fmt.Printf("Failed to write error log: %v\n", logErr)
				}
				return snapshotCreatedMsg{err: fmt.Errorf("failed to merge branch to main: %w", err), response: nil}
			}
			gitHash = &hash
		}

		req := models.CreateSnapshotRequest{
			Service: service,
			Dataset: dataset,
			GitHash: gitHash,
		}

		utils.LogDebug("Calling CreateSnapshot for: %s (service: %s)", publicID, service)
		resp, err := client.Sandbox.CreateSnapshot(ctx, publicID, req)
		if err != nil {
			// Log error to file
			utils.LogDebug("CreateSnapshot failed: %v", err)
			logErr := logErrorToFile("plato_error.log", fmt.Sprintf("API: CreateSnapshot failed for %s: %v", publicID, err))
			if logErr != nil {
				fmt.Printf("Failed to write error log: %v\n", logErr)
			}
			return snapshotCreatedMsg{err: err, response: nil}
		}

		utils.LogDebug("Snapshot created successfully: %s", resp.ArtifactID)
		return snapshotCreatedMsg{err: nil, response: resp}
	}
}

func createSnapshotWithConfig(client *plato.PlatoClient, publicID, jobGroupID, service string, dataset *string, dbConfig utils.DBConfig) tea.Cmd {
	return func() tea.Msg {
		// Step 1: Perform pre-snapshot cleanup with provided config
		utils.LogDebug("Starting pre-snapshot cleanup with provided DB config for service: %s", service)
		if err := utils.PreSnapshotCleanupWithConfig(client, publicID, jobGroupID, dbConfig); err != nil {
			utils.LogDebug("Pre-snapshot cleanup failed: %v", err)
			// Don't fail the snapshot if cleanup fails, just log it
		}

		// Step 2: Create the snapshot
		// Use a timeout context to prevent hanging (snapshots can take a while)
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		req := models.CreateSnapshotRequest{
			Service: service,
			Dataset: dataset,
		}

		utils.LogDebug("Calling CreateSnapshot for: %s (service: %s)", publicID, service)
		resp, err := client.Sandbox.CreateSnapshot(ctx, publicID, req)
		if err != nil {
			// Log error to file
			utils.LogDebug("CreateSnapshot failed: %v", err)
			logErr := logErrorToFile("plato_error.log", fmt.Sprintf("API: CreateSnapshot failed for %s: %v", publicID, err))
			if logErr != nil {
				fmt.Printf("Failed to write error log: %v\n", logErr)
			}
			return snapshotCreatedMsg{err: err, response: nil}
		}

		utils.LogDebug("Snapshot created successfully: %s", resp.ArtifactID)
		return snapshotCreatedMsg{err: nil, response: resp}
	}
}

func startWorker(client *plato.PlatoClient, publicID string, service string, dataset string, datasetConfig models.SimConfigDataset) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		req := models.StartWorkerRequest{
			Service:            service,
			Dataset:            dataset,
			PlatoDatasetConfig: datasetConfig,
			Timeout:            600, // 10 minutes timeout
		}

		resp, err := client.Sandbox.StartWorker(ctx, publicID, req)
		if err != nil {
			// Log error to file
			logErr := logErrorToFile("plato_error.log", fmt.Sprintf("API: StartWorker failed for %s: %v", publicID, err))
			if logErr != nil {
				fmt.Printf("Failed to write error log: %v\n", logErr)
			}
			return workerStartedMsg{err: err, response: nil}
		}

		return workerStartedMsg{err: nil, response: resp}
	}
}

// mergeHubBranchToMain merges a branch into main in the hub repository and returns the merge commit hash
func mergeHubBranchToMain(client *plato.PlatoClient, serviceName string, branchName string) (string, error) {
	ctx := context.Background()

	// Get Gitea credentials
	creds, err := client.Gitea.GetCredentials(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to get credentials: %w", err)
	}

	// Find simulator by service name
	simulators, err := client.Gitea.ListSimulators(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to list simulators: %w", err)
	}

	var simulator *models.GiteaSimulator
	for i := range simulators {
		if strings.EqualFold(simulators[i].Name, serviceName) {
			simulator = &simulators[i]
			break
		}
	}

	if simulator == nil {
		return "", fmt.Errorf("simulator '%s' not found in hub", serviceName)
	}

	// Get repository
	repo, err := client.Gitea.GetSimulatorRepository(ctx, simulator.ID)
	if err != nil {
		return "", fmt.Errorf("failed to get repository: %w", err)
	}

	// Build authenticated clone URL
	cloneURL := repo.CloneURL
	if strings.HasPrefix(cloneURL, "https://") {
		cloneURL = strings.Replace(cloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
	}

	// Clone repo to temp directory
	tempDir, err := os.MkdirTemp("", "plato-merge-*")
	if err != nil {
		return "", fmt.Errorf("failed to create temp dir: %w", err)
	}
	defer os.RemoveAll(tempDir)

	tempRepo := filepath.Join(tempDir, "repo")
	cloneCmd := exec.Command("git", "clone", cloneURL, tempRepo)
	if output, err := cloneCmd.CombinedOutput(); err != nil {
		return "", fmt.Errorf("failed to clone repo: %w\nOutput: %s", err, string(output))
	}

	// Checkout the branch
	gitCheckoutBranch := exec.Command("git", "checkout", branchName)
	gitCheckoutBranch.Dir = tempRepo
	if output, err := gitCheckoutBranch.CombinedOutput(); err != nil {
		return "", fmt.Errorf("failed to checkout branch: %w\nOutput: %s", err, string(output))
	}

	// Get the current commit hash from the branch
	gitRevParse := exec.Command("git", "rev-parse", "HEAD")
	gitRevParse.Dir = tempRepo
	hashOutput, err := gitRevParse.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get commit hash: %w", err)
	}
	commitHash := strings.TrimSpace(string(hashOutput))

	// Force push the branch to main (avoiding merge conflicts)
	gitPush := exec.Command("git", "push", "origin", fmt.Sprintf("%s:main", branchName), "--force")
	gitPush.Dir = tempRepo
	if output, err := gitPush.CombinedOutput(); err != nil {
		return "", fmt.Errorf("failed to push to main: %w\nOutput: %s", err, string(output))
	}

	return commitHash, nil
}

func pushToHub(client *plato.PlatoClient, serviceName string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		// Get Gitea credentials
		creds, err := client.Gitea.GetCredentials(ctx)
		if err != nil {
			logErrorToFile("plato_error.log", fmt.Sprintf("Failed to get Gitea credentials: %v", err))
			return hubPushMsg{err: fmt.Errorf("failed to get credentials: %w", err)}
		}

		// Find simulator by service name
		simulators, err := client.Gitea.ListSimulators(ctx)
		if err != nil {
			logErrorToFile("plato_error.log", fmt.Sprintf("Failed to list simulators: %v", err))
			return hubPushMsg{err: fmt.Errorf("failed to list simulators: %w", err)}
		}

		var simulator *models.GiteaSimulator
		for i := range simulators {
			if strings.EqualFold(simulators[i].Name, serviceName) {
				simulator = &simulators[i]
				break
			}
		}

		if simulator == nil {
			return hubPushMsg{err: fmt.Errorf("simulator '%s' not found in hub", serviceName)}
		}

		// Get or create repository
		var repo *models.GiteaRepository
		if simulator.HasRepo {
			repo, err = client.Gitea.GetSimulatorRepository(ctx, simulator.ID)
			if err != nil {
				return hubPushMsg{err: fmt.Errorf("failed to get repository: %w", err)}
			}
		} else {
			repo, err = client.Gitea.CreateSimulatorRepository(ctx, simulator.ID)
			if err != nil {
				return hubPushMsg{err: fmt.Errorf("failed to create repository: %w", err)}
			}
		}

		// Build authenticated clone URL
		cloneURL := repo.CloneURL
		if strings.HasPrefix(cloneURL, "https://") {
			cloneURL = strings.Replace(cloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
		}

		// Clone repo to temp directory
		tempDir, err := os.MkdirTemp("", "plato-hub-*")
		if err != nil {
			return hubPushMsg{err: fmt.Errorf("failed to create temp dir: %w", err)}
		}
		defer os.RemoveAll(tempDir)

		tempRepo := filepath.Join(tempDir, "repo")
		cloneCmd := exec.Command("git", "clone", cloneURL, tempRepo)
		cloneOutput, err := cloneCmd.CombinedOutput()
		if err != nil {
			return hubPushMsg{err: fmt.Errorf("failed to clone repo: %w\nOutput: %s", err, string(cloneOutput))}
		}

		// Get current directory
		currentDir, err := os.Getwd()
		if err != nil {
			return hubPushMsg{err: fmt.Errorf("failed to get current directory: %w", err)}
		}

		// Generate branch name with timestamp
		branchName := fmt.Sprintf("workspace-%d", time.Now().Unix())

		// Create and checkout new branch
		gitCheckout := exec.Command("git", "checkout", "-b", branchName)
		gitCheckout.Dir = tempRepo
		if output, err := gitCheckout.CombinedOutput(); err != nil {
			return hubPushMsg{err: fmt.Errorf("git checkout failed: %w\nOutput: %s", err, string(output))}
		}

		// Copy files respecting .gitignore
		if err := copyFilesRespectingGitignore(currentDir, tempRepo); err != nil {
			return hubPushMsg{err: fmt.Errorf("failed to copy files: %w", err)}
		}

		// Commit and push
		gitAdd := exec.Command("git", "add", ".")
		gitAdd.Dir = tempRepo
		if output, err := gitAdd.CombinedOutput(); err != nil {
			return hubPushMsg{err: fmt.Errorf("git add failed: %w\nOutput: %s", err, string(output))}
		}

		// Check if there are changes
		gitStatus := exec.Command("git", "status", "--porcelain")
		gitStatus.Dir = tempRepo
		statusOutput, err := gitStatus.Output()
		if err != nil {
			return hubPushMsg{err: fmt.Errorf("git status failed: %w", err)}
		}

		if len(strings.TrimSpace(string(statusOutput))) == 0 {
			// No changes to push - still return authenticated clone URL
			authenticatedCloneURL := repo.CloneURL
			if strings.HasPrefix(authenticatedCloneURL, "https://") {
				authenticatedCloneURL = strings.Replace(authenticatedCloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
			}
			return hubPushMsg{err: nil, repoURL: repo.CloneURL, cloneCmd: fmt.Sprintf("git clone -b %s %s", branchName, authenticatedCloneURL), branchName: branchName}
		}

		// Commit changes
		gitCommit := exec.Command("git", "commit", "-m", fmt.Sprintf("Sync from local workspace"))
		gitCommit.Dir = tempRepo
		if output, err := gitCommit.CombinedOutput(); err != nil {
			return hubPushMsg{err: fmt.Errorf("git commit failed: %w\nOutput: %s", err, string(output))}
		}

		// Push to remote branch
		gitPush := exec.Command("git", "push", "-u", "origin", branchName)
		gitPush.Dir = tempRepo
		if output, err := gitPush.CombinedOutput(); err != nil {
			return hubPushMsg{err: fmt.Errorf("git push failed: %w\nOutput: %s", err, string(output))}
		}

		// Build authenticated clone URL for the user
		authenticatedCloneURL := repo.CloneURL
		if strings.HasPrefix(authenticatedCloneURL, "https://") {
			authenticatedCloneURL = strings.Replace(authenticatedCloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
		}

		// Return success with authenticated clone command
		cloneCommand := fmt.Sprintf("git clone -b %s %s", branchName, authenticatedCloneURL)
		return hubPushMsg{err: nil, repoURL: repo.CloneURL, cloneCmd: cloneCommand, branchName: branchName}
	}
}

// startService pushes code to hub, clones it on the VM, and starts services
func startService(client *plato.PlatoClient, serviceName string, datasetName string, datasetConfig models.SimConfigDataset, sshHost string, sshConfigPath string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		// Step 1: Push code to hub (reuse pushToHub logic)
		utils.LogDebug("Step 1: Pushing code to hub for service: %s", serviceName)

		// Get Gitea credentials
		creds, err := client.Gitea.GetCredentials(ctx)
		if err != nil {
			return serviceStartedMsg{err: fmt.Errorf("failed to get credentials: %w", err)}
		}

		// Find simulator by service name
		simulators, err := client.Gitea.ListSimulators(ctx)
		if err != nil {
			return serviceStartedMsg{err: fmt.Errorf("failed to list simulators: %w", err)}
		}

		var simulator *models.GiteaSimulator
		for i := range simulators {
			if strings.EqualFold(simulators[i].Name, serviceName) {
				simulator = &simulators[i]
				break
			}
		}

		if simulator == nil {
			return serviceStartedMsg{err: fmt.Errorf("simulator '%s' not found in hub", serviceName)}
		}

		// Get or create repository
		var repo *models.GiteaRepository
		if simulator.HasRepo {
			repo, err = client.Gitea.GetSimulatorRepository(ctx, simulator.ID)
			if err != nil {
				return serviceStartedMsg{err: fmt.Errorf("failed to get repository: %w", err)}
			}
		} else {
			repo, err = client.Gitea.CreateSimulatorRepository(ctx, simulator.ID)
			if err != nil {
				return serviceStartedMsg{err: fmt.Errorf("failed to create repository: %w", err)}
			}
		}

		// Build authenticated clone URL
		cloneURL := repo.CloneURL
		if strings.HasPrefix(cloneURL, "https://") {
			cloneURL = strings.Replace(cloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
		}

		// Clone repo to temp directory
		tempDir, err := os.MkdirTemp("", "plato-hub-*")
		if err != nil {
			return serviceStartedMsg{err: fmt.Errorf("failed to create temp dir: %w", err)}
		}
		defer os.RemoveAll(tempDir)

		tempRepo := filepath.Join(tempDir, "repo")
		cloneCmd := exec.Command("git", "clone", cloneURL, tempRepo)
		cloneOutput, err := cloneCmd.CombinedOutput()
		if err != nil {
			return serviceStartedMsg{err: fmt.Errorf("failed to clone repo: %w\nOutput: %s", err, string(cloneOutput))}
		}

		// Get current directory
		currentDir, err := os.Getwd()
		if err != nil {
			return serviceStartedMsg{err: fmt.Errorf("failed to get current directory: %w", err)}
		}

		// Generate branch name with timestamp
		branchName := fmt.Sprintf("workspace-%d", time.Now().Unix())

		// Create and checkout new branch
		gitCheckout := exec.Command("git", "checkout", "-b", branchName)
		gitCheckout.Dir = tempRepo
		if output, err := gitCheckout.CombinedOutput(); err != nil {
			return serviceStartedMsg{err: fmt.Errorf("git checkout failed: %w\nOutput: %s", err, string(output))}
		}

		// Copy files respecting .gitignore
		if err := copyFilesRespectingGitignore(currentDir, tempRepo); err != nil {
			return serviceStartedMsg{err: fmt.Errorf("failed to copy files: %w", err)}
		}

		// Commit and push
		gitAdd := exec.Command("git", "add", ".")
		gitAdd.Dir = tempRepo
		if output, err := gitAdd.CombinedOutput(); err != nil {
			return serviceStartedMsg{err: fmt.Errorf("git add failed: %w\nOutput: %s", err, string(output))}
		}

		// Check if there are changes
		gitStatus := exec.Command("git", "status", "--porcelain")
		gitStatus.Dir = tempRepo
		statusOutput, err := gitStatus.Output()
		if err != nil {
			return serviceStartedMsg{err: fmt.Errorf("git status failed: %w", err)}
		}

		// Commit and push if there are changes, otherwise push the branch anyway
		if len(strings.TrimSpace(string(statusOutput))) > 0 {
			gitCommit := exec.Command("git", "commit", "-m", fmt.Sprintf("Sync from local workspace"))
			gitCommit.Dir = tempRepo
			if output, err := gitCommit.CombinedOutput(); err != nil {
				return serviceStartedMsg{err: fmt.Errorf("git commit failed: %w\nOutput: %s", err, string(output))}
			}
		}

		// Always push the branch (even if no changes, to ensure it exists on remote)
		gitPush := exec.Command("git", "push", "-u", "origin", branchName)
		gitPush.Dir = tempRepo
		if output, err := gitPush.CombinedOutput(); err != nil {
			return serviceStartedMsg{err: fmt.Errorf("git push failed: %w\nOutput: %s", err, string(output))}
		}

		utils.LogDebug("Code pushed successfully, branch: %s", branchName)

		// Step 2: Clone repo on VM via SSH
		utils.LogDebug("Step 2: Cloning repo on VM via SSH")

		// Build authenticated clone URL for SSH command
		authenticatedCloneURL := repo.CloneURL
		if strings.HasPrefix(authenticatedCloneURL, "https://") {
			authenticatedCloneURL = strings.Replace(authenticatedCloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
		}

		// Determine target directory on VM - use /home/plato/worktree
		repoDir := fmt.Sprintf("/home/plato/worktree/%s", serviceName)

		// Ensure worktree directory exists
		mkdirCmd := exec.Command("ssh", "-F", sshConfigPath, sshHost, "mkdir -p /home/plato/worktree")
		if output, err := mkdirCmd.CombinedOutput(); err != nil {
			utils.LogDebug("Failed to create worktree directory: %v\nOutput: %s", err, string(output))
		}

		// Remove existing directory if it exists
		rmCmd := exec.Command("ssh", "-F", sshConfigPath, sshHost, fmt.Sprintf("rm -rf %s", repoDir))
		if output, err := rmCmd.CombinedOutput(); err != nil {
			utils.LogDebug("Failed to remove existing directory (may not exist): %v\nOutput: %s", err, string(output))
		}

		// Clone the repository on the VM
		cloneVMCmd := exec.Command("ssh", "-F", sshConfigPath, sshHost, fmt.Sprintf("git clone -b %s %s %s", branchName, authenticatedCloneURL, repoDir))
		cloneVMOutput, err := cloneVMCmd.CombinedOutput()
		if err != nil {
			return serviceStartedMsg{err: fmt.Errorf("failed to clone repo on VM: %w\nOutput: %s", err, string(cloneVMOutput))}
		}

		utils.LogDebug("Repo cloned on VM: %s", string(cloneVMOutput))

		// Step 3: Start services based on their type
		utils.LogDebug("Step 3: Starting services from dataset config")
		var servicesInfo []string

		for serviceName, service := range datasetConfig.Services {
			if service == nil {
				continue
			}

			utils.LogDebug("Starting service: %s (type: %s)", serviceName, service.Type)

			switch service.Type {
			case "docker-compose":
				// Run docker compose up (Docker Compose V2)
				composeFile := service.File
				if composeFile == "" {
					composeFile = "docker-compose.yml"
				}

				// Build the docker compose command (V2 syntax without hyphen)
				// Set DOCKER_HOST to use rootless docker daemon socket
				composeCmd := fmt.Sprintf("cd %s && DOCKER_HOST=unix:///var/run/docker-user.sock docker compose -f %s up -d", repoDir, composeFile)
				sshCmd := exec.Command("ssh", "-F", sshConfigPath, sshHost, composeCmd)

				output, err := sshCmd.CombinedOutput()
				if err != nil {
					return serviceStartedMsg{err: fmt.Errorf("failed to start docker compose service '%s': %w\nOutput: %s", serviceName, err, string(output))}
				}

				utils.LogDebug("Docker compose service '%s' started: %s", serviceName, string(output))
				servicesInfo = append(servicesInfo, fmt.Sprintf("✓ Started docker compose service: %s", serviceName))

			default:
				utils.LogDebug("Unknown service type: %s for service: %s", service.Type, serviceName)
				servicesInfo = append(servicesInfo, fmt.Sprintf("⚠ Skipped service '%s' (unknown type: %s)", serviceName, service.Type))
			}
		}

		return serviceStartedMsg{
			err:          nil,
			repoURL:      repo.CloneURL,
			branchName:   branchName,
			servicesInfo: servicesInfo,
		}
	}
}

// authenticateECR authenticates Docker with AWS ECR on the VM.
// ECR authentication tokens are valid for 12 hours by default.
// This function is called automatically when the VM starts up.
func authenticateECR(sshHost string, sshConfigPath string) tea.Cmd {
	return func() tea.Msg {
		utils.LogDebug("Starting ECR authentication process")

		// Step 1: Get ECR login token on local machine
		utils.LogDebug("Step 1: Getting ECR login token from local AWS CLI")
		ecrCmd := exec.Command("aws", "ecr", "get-login-password", "--region", "us-west-1")
		tokenBytes, err := ecrCmd.Output()
		if err != nil {
			return ecrAuthenticatedMsg{err: fmt.Errorf("failed to get ECR login token: %w", err)}
		}

		token := strings.TrimSpace(string(tokenBytes))
		if token == "" {
			return ecrAuthenticatedMsg{err: fmt.Errorf("ECR login token is empty")}
		}

		utils.LogDebug("Successfully got ECR login token (length: %d)", len(token))

		// Step 2: Login to ECR on the VM using the token
		utils.LogDebug("Step 2: Logging into ECR on VM")
		ecrRegistry := "383806609161.dkr.ecr.us-west-1.amazonaws.com"

		// Use echo to pipe the token to docker login
		// Set DOCKER_HOST to use rootless docker daemon socket
		dockerLoginCmd := fmt.Sprintf("echo '%s' | DOCKER_HOST=unix:///var/run/docker-user.sock docker login --username AWS --password-stdin %s", token, ecrRegistry)
		sshCmd := exec.Command("ssh", "-F", sshConfigPath, sshHost, dockerLoginCmd)

		output, err := sshCmd.CombinedOutput()
		if err != nil {
			return ecrAuthenticatedMsg{err: fmt.Errorf("failed to login to ECR on VM: %w\nOutput: %s", err, string(output))}
		}

		utils.LogDebug("ECR authentication successful: %s", string(output))
		return ecrAuthenticatedMsg{err: nil}
	}
}

// copyFilesRespectingGitignore copies files from src to dst respecting .gitignore
func copyFilesRespectingGitignore(src, dst string) error {
	// First copy .gitignore if it exists
	gitignoreSrc := filepath.Join(src, ".gitignore")
	if _, err := os.Stat(gitignoreSrc); err == nil {
		gitignoreDst := filepath.Join(dst, ".gitignore")
		if _, err := os.Stat(gitignoreDst); os.IsNotExist(err) {
			input, err := os.ReadFile(gitignoreSrc)
			if err != nil {
				return err
			}
			if err := os.WriteFile(gitignoreDst, input, 0644); err != nil {
				return err
			}
		}
	}

	// Helper to check if path should be copied
	shouldCopy := func(path string) bool {
		baseName := filepath.Base(path)
		// Skip .git directories and .plato-hub.json
		if strings.HasPrefix(baseName, ".git") || baseName == ".plato-hub.json" {
			return false
		}

		// Use git check-ignore to respect .gitignore rules
		cmd := exec.Command("git", "check-ignore", "-q", path)
		cmd.Dir = src
		err := cmd.Run()
		// git check-ignore returns 0 if path IS ignored, 1 if NOT ignored
		return err != nil // Return true if NOT ignored
	}

	// Walk through source directory
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Get relative path
		relPath, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}

		// Skip root directory
		if relPath == "." {
			return nil
		}

		// Check if should copy
		if !shouldCopy(path) {
			if info.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}

		dstPath := filepath.Join(dst, relPath)

		if info.IsDir() {
			return os.MkdirAll(dstPath, info.Mode())
		}

		// Copy file
		input, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(dstPath, input, info.Mode())
	})
}

// These functions are now in internal/utils/network.go
// Keeping empty stubs here for reference, but they should be removed
// and all calls should use utils.FindFreePort() and utils.FindFreePortPreferred()

func openProxytunnelWithPort(client *plato.PlatoClient, publicID string, remotePort int) tea.Cmd {
	return func() tea.Msg {
		utils.LogDebug("openProxytunnelWithPort called, publicID=%s, remotePort=%d", publicID, remotePort)

		// Try to use the same port as remote, fall back to any free port
		localPort, err := utils.FindFreePortPreferred(remotePort)
		if err != nil {
			utils.LogDebug("Failed to find free port: %v", err)
			return proxytunnelOpenedMsg{err: fmt.Errorf("failed to find free port: %w", err)}
		}
		utils.LogDebug("Found free local port: %d (requested: %d)", localPort, remotePort)

		// Find proxytunnel path
		proxytunnelPath, err := exec.LookPath("proxytunnel")
		if err != nil {
			utils.LogDebug("proxytunnel not found: %v", err)
			return proxytunnelOpenedMsg{err: fmt.Errorf("proxytunnel not found in PATH: %w", err)}
		}
		utils.LogDebug("Found proxytunnel at: %s", proxytunnelPath)

		// Get proxy configuration based on base URL
		proxyConfig := utils.GetProxyConfig(client.GetBaseURL())
		utils.LogDebug("Using proxy server: %s (secure: %v)", proxyConfig.Server, proxyConfig.Secure)

		// Build proxytunnel command arguments
		args := []string{}
		if proxyConfig.Secure {
			args = append(args, "-E")
		}
		args = append(args,
			"-p", proxyConfig.Server,
			"-P", fmt.Sprintf("%s@%d:newpass", publicID, remotePort),
			"-d", fmt.Sprintf("127.0.0.1:%d", remotePort),
			"-a", fmt.Sprintf("%d", localPort),
			"-v",
			"--no-check-certificate",
		)

		cmd := exec.Command(proxytunnelPath, args...)
		utils.LogDebug("Starting proxytunnel command: %v", cmd.Args)

		// Start the process
		if err := cmd.Start(); err != nil {
			utils.LogDebug("Failed to start proxytunnel: %v", err)
			return proxytunnelOpenedMsg{err: fmt.Errorf("failed to start proxytunnel: %w", err)}
		}
		utils.LogDebug("Proxytunnel started successfully with PID: %d", cmd.Process.Pid)

		return proxytunnelOpenedMsg{
			localPort:  localPort,
			remotePort: remotePort,
			cmd:        cmd,
			err:        nil,
		}
	}
}

func setupRootPassword(client *plato.PlatoClient, publicID string, privateKeyPath string, sshHost string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		utils.LogDebug("Setting up root SSH access for VM: %s", publicID)

		// Determine the correct public key path
		var publicKeyPath string
		if privateKeyPath != "" && filepath.IsAbs(privateKeyPath) {
			// Use the provided private key path
			publicKeyPath = privateKeyPath + ".pub"
		}

		// Read the generated SSH public key for this VM
		publicKeyData, err := os.ReadFile(publicKeyPath)
		if err != nil {
			utils.LogDebug("Failed to read SSH public key from %s: %v", publicKeyPath, err)
			logErrorToFile("plato_error.log", fmt.Sprintf("Failed to read SSH public key: %v", err))
			return rootPasswordSetupMsg{err: fmt.Errorf("failed to read SSH public key from %s: %w", publicKeyPath, err)}
		}
		sshPublicKey := strings.TrimSpace(string(publicKeyData))

		// Call the SetupRootPassword API with SSH public key
		err = client.Sandbox.SetupRootPassword(ctx, publicID, sshPublicKey)
		if err != nil {
			utils.LogDebug("SetupRootPassword API failed: %v", err)
			logErrorToFile("plato_error.log", fmt.Sprintf("API: SetupRootPassword failed for %s: %v", publicID, err))
			return rootPasswordSetupMsg{err: fmt.Errorf("failed to set up root SSH access: %w", err)}
		}

		utils.LogDebug("Root SSH access setup successful for VM: %s", publicID)
		return rootPasswordSetupMsg{err: nil}
	}
}

func openCursor(sshHost string, sshConfigPath string) tea.Cmd {
	return func() tea.Msg {
		utils.LogDebug("Opening VS Code for SSH host: %s with config: %s", sshHost, sshConfigPath)

		// Read the temp SSH config and append it to the user's main SSH config
		// This allows VSCode Remote SSH to find the host
		tempConfig, err := os.ReadFile(sshConfigPath)
		if err != nil {
			utils.LogDebug("Failed to read temp SSH config: %v", err)
			return cursorOpenedMsg{err: fmt.Errorf("failed to read SSH config: %w", err)}
		}

		// Read existing SSH config
		existingConfig, err := utils.ReadSSHConfig()
		if err != nil {
			utils.LogDebug("Failed to read existing SSH config: %v", err)
			return cursorOpenedMsg{err: fmt.Errorf("failed to read existing SSH config: %w", err)}
		}

		// Check if host already exists
		if !strings.Contains(existingConfig, fmt.Sprintf("Host %s", sshHost)) {
			// Append temp config to user's SSH config
			newConfig := existingConfig
			if newConfig != "" && !strings.HasSuffix(newConfig, "\n\n") {
				newConfig += "\n\n"
			}
			newConfig += string(tempConfig)

			if err := utils.WriteSSHConfig(newConfig); err != nil {
				utils.LogDebug("Failed to write SSH config: %v", err)
				return cursorOpenedMsg{err: fmt.Errorf("failed to update SSH config: %w", err)}
			}
			utils.LogDebug("Added SSH host to ~/.ssh/config")
		}

		// Find code command
		codePath, err := exec.LookPath("code")
		if err != nil {
			utils.LogDebug("code command not found: %v", err)
			return cursorOpenedMsg{err: fmt.Errorf("code command not found in PATH. Please install VS Code: https://code.visualstudio.com")}
		}
		utils.LogDebug("Found code at: %s", codePath)

		// Build code command with SSH remote
		cmd := exec.Command(codePath, "--folder-uri", fmt.Sprintf("vscode-remote://ssh-remote+%s/root", sshHost), "--remote-platform", "linux")

		utils.LogDebug("Starting code command: %v", cmd.Args)

		// Start the code process (don't wait, let it run independently)
		if err := cmd.Start(); err != nil {
			utils.LogDebug("Failed to start code: %v", err)
			return cursorOpenedMsg{err: fmt.Errorf("failed to start code: %w", err)}
		}

		utils.LogDebug("VS Code started successfully with PID: %d", cmd.Process.Pid)

		// Release the process so it continues independently
		go cmd.Wait()

		return cursorOpenedMsg{err: nil}
	}
}

func (m VMInfoModel) handleAction(action vmAction) (VMInfoModel, tea.Cmd) {
	switch action.title {
	case "Start Plato Worker":
		// Load the config to get dataset configuration
		config, err := LoadPlatoConfig()
		if err != nil {
			errMsg := fmt.Sprintf("❌ Failed to load plato-config.yml: %v", err)
			m.statusMessages = append(m.statusMessages, errMsg)
			logErrorToFile("plato_error.log", errMsg)
			return m, nil
		}

		// Get dataset config
		datasetConfig, exists := config.Datasets[m.dataset]
		if !exists {
			errMsg := fmt.Sprintf("❌ Dataset '%s' not found in plato-config.yml", m.dataset)
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

		m.statusMessages = append(m.statusMessages, fmt.Sprintf("Starting Plato worker for service: %s, dataset: %s", service, m.dataset))
		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, startWorker(m.client, m.sandbox.PublicID, service, m.dataset, datasetConfig))
	case "Set up root SSH":
		// Check if root password is already set up
		if m.rootPasswordSetup {
			m.statusMessages = append(m.statusMessages, "⚠️  Root SSH password is already configured")
			return m, nil
		}

		// Check if SSH host is configured
		if m.sshHost == "" {
			m.statusMessages = append(m.statusMessages, "❌ SSH host not configured. Cannot set up root SSH.")
			return m, nil
		}

		m.statusMessages = append(m.statusMessages, "Setting up root SSH password...")
		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, setupRootPassword(m.client, m.sandbox.PublicID, m.sshPrivateKeyPath, m.sshHost))
	case "Connect to Cursor/VSCode":
		if m.sshHost == "" {
			m.statusMessages = append(m.statusMessages, "❌ SSH host not set up yet")
			return m, nil
		}
		if m.sshConfigPath == "" {
			m.statusMessages = append(m.statusMessages, "❌ SSH config not set up yet")
			return m, nil
		}

		// Launch VS Code connected to the VM via SSH
		m.statusMessages = append(m.statusMessages, "Opening VS Code...")
		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, openCursor(m.sshHost, m.sshConfigPath))
	case "Advanced":
		// Navigate to advanced menu
		return m, func() tea.Msg {
			// Create and navigate to the advanced menu
			return NavigateMsg{view: ViewAdvanced}
		}
	case "Start Service":
		// Load the config to get service name and dataset config
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

		// Get dataset config
		datasetConfig, exists := config.Datasets[m.dataset]
		if !exists {
			errMsg := fmt.Sprintf("❌ Dataset '%s' not found in plato-config.yml", m.dataset)
			m.statusMessages = append(m.statusMessages, errMsg)
			logErrorToFile("plato_error.log", errMsg)
			return m, nil
		}

		m.statusMessages = append(m.statusMessages, fmt.Sprintf("Starting service: %s", service))
		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, startService(m.client, service, m.dataset, datasetConfig, m.sshHost, m.sshConfigPath))
	case "Snapshot VM":
		// Load the config to get service
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

		// Navigate to dataset selector to let user choose which dataset to snapshot as
		return m, func() tea.Msg {
			return navigateToDatasetSelectorMsg{
				service:          service,
				publicID:         m.sandbox.PublicID,
				jobGroupID:       m.sandbox.JobGroupID,
				lastPushedBranch: m.lastPushedBranch,
			}
		}
	case "Close VM":
		// Stop heartbeat goroutine (only if not already stopped)
		if !m.heartbeatStopped {
			close(m.heartbeatStop)
			m.heartbeatStopped = true
			utils.LogDebug("Stopped heartbeat goroutine")
		}
		// Kill all proxytunnel processes
		for i, cmd := range m.proxytunnelProcesses {
			if cmd.Process != nil {
				pid := cmd.Process.Pid
				utils.LogDebug("Killing proxytunnel process %d/%d (PID: %d)", i+1, len(m.proxytunnelProcesses), pid)
				if err := cmd.Process.Kill(); err != nil {
					utils.LogDebug("Error killing proxytunnel process PID %d: %v", pid, err)
				} else {
					utils.LogDebug("Successfully killed proxytunnel process PID: %d", pid)
					// Wait for process to exit to avoid zombies
					go cmd.Wait()
				}
			} else {
				utils.LogDebug("Proxytunnel process %d/%d has no process handle", i+1, len(m.proxytunnelProcesses))
			}
		}
		utils.LogDebug("Finished killing %d proxytunnel processes", len(m.proxytunnelProcesses))

		// Cleanup SSH config entry if exists
		if m.sshHost != "" {
			if err := utils.CleanupSSHConfig(m.sshHost); err != nil {
				utils.LogDebug("Error cleaning up SSH config: %v", err)
			} else {
				utils.LogDebug("Successfully cleaned up SSH config for host: %s", m.sshHost)
			}
		}

		// Delete the temporary SSH config file
		if m.sshConfigPath != "" {
			if err := os.Remove(m.sshConfigPath); err != nil {
				utils.LogDebug("Error removing SSH config file %s: %v", m.sshConfigPath, err)
			} else {
				utils.LogDebug("Successfully removed SSH config file: %s", m.sshConfigPath)
			}
		}

		// Delete the SSH key pair files
		if m.sshPrivateKeyPath != "" {
			if err := utils.CleanupSSHKeyPair(m.sshPrivateKeyPath); err != nil {
				utils.LogDebug("Error cleaning up SSH key pair: %v", err)
			} else {
				utils.LogDebug("Successfully cleaned up SSH key pair: %s", m.sshPrivateKeyPath)
			}
		}
		// Call VM cleanup API
		return m, func() tea.Msg {
			// Use a timeout context to prevent hanging
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()

			utils.LogDebug("Calling DeleteVM for: %s", m.sandbox.PublicID)
			if err := m.client.Sandbox.DeleteVM(ctx, m.sandbox.PublicID); err != nil {
				// Log error but still navigate away
				utils.LogDebug("Warning: failed to delete VM: %v", err)
			} else {
				utils.LogDebug("Successfully deleted VM: %s", m.sandbox.PublicID)
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

	// If setting up or running a command, show spinner and status
	if m.settingUp || m.runningCommand {
		statusMsgStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#CCCCCC"))

		prevStatusStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#888888"))

		// Calculate max width for wrapping (accounting for margins and indentation)
		maxWidth := m.width - 10
		if maxWidth < 40 {
			maxWidth = 40 // Minimum width
		}

		var statusContent strings.Builder
		for i, msg := range m.statusMessages {
			if i == len(m.statusMessages)-1 {
				// Current status with spinner
				text := fmt.Sprintf("%s %s", m.spinner.View(), msg)
				wrapped := wrapText(text, maxWidth)
				// Add indentation to each line
				lines := strings.Split(wrapped, "\n")
				for j, line := range lines {
					if j == 0 {
						statusContent.WriteString(statusMsgStyle.Render("  "+line) + "\n")
					} else {
						statusContent.WriteString(statusMsgStyle.Render("    "+line) + "\n")
					}
				}
			} else {
				// Previous completed status
				text := fmt.Sprintf("✓ %s", msg)
				wrapped := wrapText(text, maxWidth)
				// Add indentation to each line
				lines := strings.Split(wrapped, "\n")
				for j, line := range lines {
					if j == 0 {
						statusContent.WriteString(prevStatusStyle.Render("    "+line) + "\n")
					} else {
						statusContent.WriteString(prevStatusStyle.Render("      "+line) + "\n")
					}
				}
			}
		}

		body := lipgloss.NewStyle().MarginTop(1).Render(statusContent.String())
		return components.RenderHeader() + "\n" + header + "\n" + body
	}

	// Actions panel (left side) - no border, just margin
	actionsPanel := m.lg.NewStyle().
		Margin(1, 4, 1, 0).
		Render(m.actionList.View())

	// Info panel (right side) - change border brightness based on focus
	var borderColor lipgloss.Color
	if m.infoPanelFocused {
		borderColor = lipgloss.Color("#7D56F4") // Bright purple when focused
	} else {
		borderColor = lipgloss.Color("#444444") // Dark gray when not focused
	}

	m.viewport.Style = lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderColor).
		PaddingLeft(1)

	vmInfoPanel := m.viewport.View()
	body := lipgloss.JoinHorizontal(lipgloss.Left, actionsPanel, vmInfoPanel)

	helpStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("240")).
		MarginTop(1).
		MarginLeft(2)

	// Update help text based on which panel is focused
	var helpText string
	if m.infoPanelFocused {
		helpText = "↑/↓: scroll • pgup/pgdn: page • i: focus actions • ctrl+c: quit"
	} else {
		helpText = "enter: select action • i: focus info • ctrl+c: quit"
	}
	footer := helpStyle.Render(helpText)

	return components.RenderHeader() + "\n" + header + "\n" + body + "\n" + footer
}

// fetchHubRepoURL fetches the hub repository URL for a service
func fetchHubRepoURL(client *plato.PlatoClient, serviceName string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		// Fetch simulators
		simulators, err := client.Gitea.ListSimulators(ctx)
		if err != nil {
			return hubRepoURLMsg{url: ""}
		}

		// Find the simulator by service name
		for _, sim := range simulators {
			if strings.EqualFold(sim.Name, serviceName) {
				if sim.HasRepo {
					// Get the repository
					repo, err := client.Gitea.GetSimulatorRepository(ctx, sim.ID)
					if err == nil {
						// Return the CloneURL without .git suffix
						hubURL := strings.TrimSuffix(repo.CloneURL, ".git")
						return hubRepoURLMsg{url: hubURL}
					}
				}
				break
			}
		}

		return hubRepoURLMsg{url: ""}
	}
}

// getSandboxPublicURL computes the public URL for a sandbox based on the base URL
func getSandboxPublicURL(client *plato.PlatoClient, sandbox *models.Sandbox) string {
	baseURL := client.GetBaseURL()
	identifier := sandbox.JobGroupID
	if identifier == "" {
		identifier = sandbox.PublicID
	}

	// Determine environment based on base_url
	if strings.Contains(baseURL, "localhost:8080") {
		return fmt.Sprintf("http://%s.sims.localhost:8080", identifier)
	} else if strings.Contains(baseURL, "plato.so") {
		// Parse subdomain from base URL
		parts := strings.Split(baseURL, ".")
		if len(parts) >= 3 {
			// Extract subdomain (e.g., "dev", "staging")
			subdomain := strings.TrimPrefix(parts[0], "https://")
			subdomain = strings.TrimPrefix(subdomain, "http://")
			if subdomain != "plato" {
				return fmt.Sprintf("https://%s.%s.sims.plato.so", identifier, subdomain)
			}
		}
		return fmt.Sprintf("https://%s.sims.plato.so", identifier)
	}

	return ""
}
