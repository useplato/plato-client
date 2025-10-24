package main

import (
	"context"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	plato "plato-sdk"
	"plato-sdk/models"

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
	showInfoPanel        bool   // Whether to show the info panel
	runningCommand       bool   // Whether a command is currently running
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

func NewVMInfoModel(client *plato.PlatoClient, sandbox *models.Sandbox, dataset string, fromExistingSim bool, artifactID *string, version *string) VMInfoModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	items := []list.Item{
		vmAction{title: "Start Plato Worker", description: "Start the Plato worker process"},
		vmAction{title: "Set up root SSH", description: "Configure root SSH password access"},
		vmAction{title: "Connect via SSH", description: "Open SSH connection to VM"},
		vmAction{title: "Connect to Cursor/VSCode", description: "Open Cursor/VSCode editor connected to VM via SSH"},
		vmAction{title: "Open Proxytunnel", description: "Create local port forward to VM"},
		vmAction{title: "Push to Plato Hub", description: "Push code to hub.plato.so repository"},
		vmAction{title: "Snapshot VM", description: "Create snapshot of current VM state"},
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
		showInfoPanel:        false, // Start with info panel hidden
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
			// If this is a completion message, clear running state
			if strings.Contains(msg.message, "complete!") || strings.Contains(msg.message, "✓") {
				m.runningCommand = false
			}
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
		logDebug("rootPasswordSetupMsg received, err: %v", msg.err)
		m.runningCommand = false
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
		return m, nil

	case workerStartedMsg:
		if msg.err != nil {
			m.runningCommand = false
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Worker start failed: %v", msg.err))
		} else if msg.response != nil {
			m.statusMessages = append(m.statusMessages, "✓ Worker start initiated!")
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Status: %s", msg.response.Status))
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("   Monitoring progress via correlation ID: %s", msg.response.CorrelationID))
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
		return m, nil

	case proxytunnelOpenedMsg:
		logDebug("proxytunnelOpenedMsg received, localPort=%d, remotePort=%d, err=%v", msg.localPort, msg.remotePort, msg.err)
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
			logDebug("Added to lists, now have %d processes and %d mappings", len(m.proxytunnelProcesses), len(m.proxytunnelMappings))
		}
		return m, nil

	case cursorOpenedMsg:
		logDebug("cursorOpenedMsg received, err=%v", msg.err)
		m.runningCommand = false
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to open Cursor: %v", msg.err))
		} else {
			m.statusMessages = append(m.statusMessages, "✓ Cursor opened successfully")
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
		m.viewport.Height = 24
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "i":
			// Toggle info panel visibility
			m.showInfoPanel = !m.showInfoPanel
			if m.showInfoPanel {
				// Update viewport content when showing
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

		// Only update action list if info panel is not shown
		// This allows viewport to handle arrow keys when shown
		if !m.showInfoPanel {
			m.actionList, cmd = m.actionList.Update(msg)
			cmds = append(cmds, cmd)
		} else {
			// When info panel is shown, viewport handles scrolling
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
	output.WriteString(fmt.Sprintf("URL:      %s\n", m.sandbox.URL))

	if m.setupComplete {
		output.WriteString("\n" + strings.Repeat("─", 50) + "\n\n")
		output.WriteString("CONNECTION INFO\n\n")
		if m.sshHost != "" {
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
		// Show last 5 messages
		start := 0
		if len(m.statusMessages) > 5 {
			start = len(m.statusMessages) - 5
		}
		for _, msg := range m.statusMessages[start:] {
			output.WriteString(fmt.Sprintf("  %s\n", msg))
		}
	}

	return output.String()
}

func createSnapshotWithCleanup(client *plato.PlatoClient, publicID, jobGroupID, service string, dataset *string, branchName string) tea.Cmd {
	return func() tea.Msg {
		// Step 1: Perform pre-snapshot cleanup
		logDebug("Starting pre-snapshot cleanup for service: %s", service)
		needsDBConfig, err := preSnapshotCleanup(client, publicID, jobGroupID, service)
		if err != nil {
			logDebug("Pre-snapshot cleanup failed: %v", err)
			// Don't fail the snapshot if cleanup fails, just log it
		}
		if needsDBConfig {
			// This shouldn't happen here since we check before calling this function
			logDebug("Warning: DB config needed but not provided")
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

		logDebug("Calling CreateSnapshot for: %s (service: %s)", publicID, service)
		resp, err := client.Sandbox.CreateSnapshot(ctx, publicID, req)
		if err != nil {
			// Log error to file
			logDebug("CreateSnapshot failed: %v", err)
			logErr := logErrorToFile("plato_error.log", fmt.Sprintf("API: CreateSnapshot failed for %s: %v", publicID, err))
			if logErr != nil {
				fmt.Printf("Failed to write error log: %v\n", logErr)
			}
			return snapshotCreatedMsg{err: err, response: nil}
		}

		logDebug("Snapshot created successfully: %s", resp.ArtifactID)
		return snapshotCreatedMsg{err: nil, response: resp}
	}
}

func createSnapshotWithConfig(client *plato.PlatoClient, publicID, jobGroupID, service string, dataset *string, dbConfig DBConfig) tea.Cmd {
	return func() tea.Msg {
		// Step 1: Perform pre-snapshot cleanup with provided config
		logDebug("Starting pre-snapshot cleanup with provided DB config for service: %s", service)
		if err := preSnapshotCleanupWithConfig(client, publicID, jobGroupID, dbConfig); err != nil {
			logDebug("Pre-snapshot cleanup failed: %v", err)
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

		logDebug("Calling CreateSnapshot for: %s (service: %s)", publicID, service)
		resp, err := client.Sandbox.CreateSnapshot(ctx, publicID, req)
		if err != nil {
			// Log error to file
			logDebug("CreateSnapshot failed: %v", err)
			logErr := logErrorToFile("plato_error.log", fmt.Sprintf("API: CreateSnapshot failed for %s: %v", publicID, err))
			if logErr != nil {
				fmt.Printf("Failed to write error log: %v\n", logErr)
			}
			return snapshotCreatedMsg{err: err, response: nil}
		}

		logDebug("Snapshot created successfully: %s", resp.ArtifactID)
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

	// Checkout main branch
	gitCheckoutMain := exec.Command("git", "checkout", "main")
	gitCheckoutMain.Dir = tempRepo
	if output, err := gitCheckoutMain.CombinedOutput(); err != nil {
		return "", fmt.Errorf("failed to checkout main: %w\nOutput: %s", err, string(output))
	}

	// Merge the branch into main
	gitMerge := exec.Command("git", "merge", "--no-ff", "-m", fmt.Sprintf("Merge %s into main for snapshot", branchName), branchName)
	gitMerge.Dir = tempRepo
	if output, err := gitMerge.CombinedOutput(); err != nil {
		return "", fmt.Errorf("failed to merge branch: %w\nOutput: %s", err, string(output))
	}

	// Get the current commit hash
	gitRevParse := exec.Command("git", "rev-parse", "HEAD")
	gitRevParse.Dir = tempRepo
	hashOutput, err := gitRevParse.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get commit hash: %w", err)
	}
	commitHash := strings.TrimSpace(string(hashOutput))

	// Push main to remote
	gitPush := exec.Command("git", "push", "origin", "main")
	gitPush.Dir = tempRepo
	if output, err := gitPush.CombinedOutput(); err != nil {
		return "", fmt.Errorf("failed to push main: %w\nOutput: %s", err, string(output))
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

// findFreePort finds an available port on the local machine
func findFreePort() (int, error) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	port := listener.Addr().(*net.TCPAddr).Port
	listener.Close()
	return port, nil
}

// findFreePortPreferred tries to use the preferred port, falls back to any free port
func findFreePortPreferred(preferredPort int) (int, error) {
	// Try preferred port first
	listener, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", preferredPort))
	if err == nil {
		// Preferred port is available
		listener.Close()
		logDebug("Using preferred port: %d", preferredPort)
		return preferredPort, nil
	}

	// Preferred port not available, find any free port
	logDebug("Preferred port %d not available, finding alternative", preferredPort)
	return findFreePort()
}

func openProxytunnelWithPort(publicID string, remotePort int) tea.Cmd {
	return func() tea.Msg {
		logDebug("openProxytunnelWithPort called, publicID=%s, remotePort=%d", publicID, remotePort)

		// Try to use the same port as remote, fall back to any free port
		localPort, err := findFreePortPreferred(remotePort)
		if err != nil {
			logDebug("Failed to find free port: %v", err)
			return proxytunnelOpenedMsg{err: fmt.Errorf("failed to find free port: %w", err)}
		}
		logDebug("Found free local port: %d (requested: %d)", localPort, remotePort)

		// Find proxytunnel path
		proxytunnelPath, err := exec.LookPath("proxytunnel")
		if err != nil {
			logDebug("proxytunnel not found: %v", err)
			return proxytunnelOpenedMsg{err: fmt.Errorf("proxytunnel not found in PATH: %w", err)}
		}
		logDebug("Found proxytunnel at: %s", proxytunnelPath)

		// Build proxytunnel command
		// proxytunnel -E -p proxy.plato.so:9000 -P '{publicID}@{remotePort}:newpass' -d 127.0.0.1:{remotePort} -a {localPort} -v --no-check-certificate
		cmd := exec.Command(
			proxytunnelPath,
			"-E",
			"-p", "proxy.plato.so:9000",
			"-P", fmt.Sprintf("%s@%d:newpass", publicID, remotePort),
			"-d", fmt.Sprintf("127.0.0.1:%d", remotePort),
			"-a", fmt.Sprintf("%d", localPort),
			"-v",
			"--no-check-certificate",
		)
		logDebug("Starting proxytunnel command: %v", cmd.Args)

		// Start the process
		if err := cmd.Start(); err != nil {
			logDebug("Failed to start proxytunnel: %v", err)
			return proxytunnelOpenedMsg{err: fmt.Errorf("failed to start proxytunnel: %w", err)}
		}
		logDebug("Proxytunnel started successfully with PID: %d", cmd.Process.Pid)

		return proxytunnelOpenedMsg{
			localPort:  localPort,
			remotePort: remotePort,
			cmd:        cmd,
			err:        nil,
		}
	}
}

func setupRootPassword(client *plato.PlatoClient, publicID string, sshHost string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		logDebug("Setting up root password for VM: %s", publicID)

		// Call the SetupRootPassword API
		err := client.Sandbox.SetupRootPassword(ctx, publicID, "password")
		if err != nil {
			logDebug("SetupRootPassword API failed: %v", err)
			logErrorToFile("plato_error.log", fmt.Sprintf("API: SetupRootPassword failed for %s: %v", publicID, err))
			return rootPasswordSetupMsg{err: fmt.Errorf("failed to set up root password: %w", err)}
		}

		logDebug("Root password setup successful for VM: %s", publicID)
		return rootPasswordSetupMsg{err: nil}
	}
}

func openCursor(sshHost string) tea.Cmd {
	return func() tea.Msg {
		logDebug("Opening VS Code for SSH host: %s", sshHost)

		// Find code command
		codePath, err := exec.LookPath("code")
		if err != nil {
			logDebug("code command not found: %v", err)
			return cursorOpenedMsg{err: fmt.Errorf("code command not found in PATH. Please install VS Code: https://code.visualstudio.com")}
		}
		logDebug("Found code at: %s", codePath)

		// Build code command with SSH remote
		// code --folder-uri vscode-remote://ssh-remote+{sshHost}/root --remote-platform linux
		folderURI := fmt.Sprintf("vscode-remote://ssh-remote+%s/root", sshHost)
		cmd := exec.Command(codePath, "--folder-uri", folderURI, "--remote-platform", "linux")

		logDebug("Starting code command: %v", cmd.Args)

		// Start the code process (don't wait, let it run independently)
		if err := cmd.Start(); err != nil {
			logDebug("Failed to start code: %v", err)
			return cursorOpenedMsg{err: fmt.Errorf("failed to start code: %w", err)}
		}

		logDebug("VS Code started successfully with PID: %d", cmd.Process.Pid)

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
		return m, tea.Batch(m.spinner.Tick, setupRootPassword(m.client, m.sandbox.PublicID, m.sshHost))
	case "Connect via SSH":
		// TODO: Implement SSH connection
		m.statusMessages = append(m.statusMessages, "SSH connection not implemented yet")
	case "Connect to Cursor/VSCode":
		if m.sshHost == "" {
			m.statusMessages = append(m.statusMessages, "❌ SSH host not set up yet")
			return m, nil
		}

		// Launch VS Code connected to the VM via SSH
		m.statusMessages = append(m.statusMessages, "Opening VS Code...")
		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, openCursor(m.sshHost))
	case "Open Proxytunnel":
		// Navigate to port selector
		return m, func() tea.Msg {
			return navigateToProxytunnelPortMsg{publicID: m.sandbox.PublicID}
		}
	case "Push to Plato Hub":
		// Load the config to get service name
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

		m.statusMessages = append(m.statusMessages, fmt.Sprintf("Pushing code to Plato Hub for service: %s", service))
		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, pushToHub(m.client, service))
	case "Snapshot VM":
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

		// Check if DB config exists for this service
		_, hasConfig := getDBConfig(service)
		if !hasConfig {
			// Navigate to DB entry view
			logDebug("No DB config for service %s, navigating to DB entry", service)
			return m, func() tea.Msg {
				return navigateToDBEntryMsg{service: service}
			}
		}

		// DB config exists, proceed with snapshot
		m.statusMessages = append(m.statusMessages, "Preparing snapshot...")

		// Use the dataset from the model
		datasetPtr := &m.dataset

		// Build info message showing service, dataset, and version
		infoMsg := fmt.Sprintf("Creating snapshot for service: %s, dataset: %s", service, m.dataset)
		if m.version != nil {
			infoMsg += fmt.Sprintf(", version: %s", *m.version)
		}
		if m.lastPushedBranch != "" {
			infoMsg += fmt.Sprintf(", merging branch: %s", m.lastPushedBranch)
		}
		m.statusMessages = append(m.statusMessages, infoMsg)

		m.runningCommand = true
		return m, tea.Batch(m.spinner.Tick, createSnapshotWithCleanup(m.client, m.sandbox.PublicID, m.sandbox.JobGroupID, service, datasetPtr, m.lastPushedBranch))
	case "Close VM":
		// Stop heartbeat goroutine (only if not already stopped)
		if !m.heartbeatStopped {
			close(m.heartbeatStop)
			m.heartbeatStopped = true
			logDebug("Stopped heartbeat goroutine")
		}
		// Kill all proxytunnel processes
		for i, cmd := range m.proxytunnelProcesses {
			if cmd.Process != nil {
				pid := cmd.Process.Pid
				logDebug("Killing proxytunnel process %d/%d (PID: %d)", i+1, len(m.proxytunnelProcesses), pid)
				if err := cmd.Process.Kill(); err != nil {
					logDebug("Error killing proxytunnel process PID %d: %v", pid, err)
				} else {
					logDebug("Successfully killed proxytunnel process PID: %d", pid)
					// Wait for process to exit to avoid zombies
					go cmd.Wait()
				}
			} else {
				logDebug("Proxytunnel process %d/%d has no process handle", i+1, len(m.proxytunnelProcesses))
			}
		}
		logDebug("Finished killing %d proxytunnel processes", len(m.proxytunnelProcesses))

		// Cleanup SSH config entry if exists
		if m.sshHost != "" {
			if err := cleanupSSHConfig(m.sshHost); err != nil {
				logDebug("Error cleaning up SSH config: %v", err)
			} else {
				logDebug("Successfully cleaned up SSH config for host: %s", m.sshHost)
			}
		}
		// Call VM cleanup API
		return m, func() tea.Msg {
			// Use a timeout context to prevent hanging
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()

			logDebug("Calling DeleteVM for: %s", m.sandbox.PublicID)
			if err := m.client.Sandbox.DeleteVM(ctx, m.sandbox.PublicID); err != nil {
				// Log error but still navigate away
				logDebug("Warning: failed to delete VM: %v", err)
			} else {
				logDebug("Successfully deleted VM: %s", m.sandbox.PublicID)
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

	// Actions panel (left side)
	actionsPanel := m.lg.NewStyle().
		Margin(1, 4, 1, 0).
		Render(m.actionList.View())

	var body string
	if m.showInfoPanel {
		// Build VM info panel (right side) using viewport
		vmInfoPanel := m.viewport.View()
		body = lipgloss.JoinHorizontal(lipgloss.Left, actionsPanel, vmInfoPanel)
	} else {
		body = actionsPanel
	}

	helpStyle := m.lg.NewStyle().
		Foreground(lipgloss.Color("240")).
		MarginTop(1).
		MarginLeft(2)

	var helpText string
	if m.showInfoPanel {
		helpText = "↑/↓: scroll • pgup/pgdn: page • i: hide info • ctrl+c: quit"
	} else {
		helpText = "enter: select action • i: show info • ctrl+c: quit"
	}
	footer := helpStyle.Render(helpText)

	return RenderHeader() + "\n" + header + "\n" + body + "\n" + footer
}
