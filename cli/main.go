// Package main provides the Plato CLI application.
//
// This is the main entry point for the Plato CLI tool, which provides an interactive
// terminal UI for managing Plato simulators, environments, and sandboxes. The CLI
// uses the Bubble Tea framework to provide a view-based navigation system with
// multiple screens including main menu, configuration, simulator selection,
// environment launching, and VM management.
//
// Test change: Version bump test
package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"path/filepath"
	"time"

	"plato-cli/internal/ui/components"
	"plato-cli/internal/utils"
	plato "plato-sdk"
	"plato-sdk/models"
	"plato-sdk/services"

	tea "github.com/charmbracelet/bubbletea"
)

type ViewState int

type NavigateMsg struct {
	view ViewState
}

type navigateToVMInfoMsg struct {
	sandbox           *models.Sandbox
	dataset           string
	sshURL            string
	sshHost           string
	sshConfigPath     string
	sshPrivateKeyPath string
	fromExistingSim   bool
	artifactID        *string
	version           *string
}

type navigateToProxytunnelPortMsg struct {
	publicID string
}

type navigateToDBEntryMsg struct {
	service string
}

type navigateToDatasetSelectorMsg struct {
	service          string
	publicID         string
	jobGroupID       string
	lastPushedBranch string
}

const (
	ViewMainMenu ViewState = iota
	ViewConfig
	ViewLaunchEnvironment
	ViewVMConfig
	ViewPlatoConfig
	ViewSimSelector
	ViewSimLaunchOptions
	ViewArtifactID
	ViewVMInfo
	ViewProxytunnelPort
	ViewDBEntry
	ViewDatasetSelector
	ViewAdvanced
	ViewFlowEntry
)

type Model struct {
	currentView      ViewState
	mainMenu         MainMenuModel
	config           ConfigModel
	launch           LaunchModel
	vmConfig         VMConfigModel
	platoConfig      PlatoConfigModel
	simSelector      SimSelectorModel
	simLaunchOptions SimLaunchOptionsModel
	artifactID       ArtifactIDModel
	vmInfo           VMInfoModel
	proxytunnelPort  ProxytunnelPortModel
	dbEntry          DBEntryModel
	datasetSelector  DatasetSelectorModel
	advancedMenu     AdvancedMenuModel
	flowEntry        FlowEntryModel
	quitting         bool
}

func newModel() Model {
	config := NewConfigModel()
	return Model{
		currentView:      ViewMainMenu,
		mainMenu:         NewMainMenuModel(),
		config:           config,
		launch:           NewLaunchModel(config.client),
		vmConfig:         NewVMConfigModel(config.client, nil, nil, nil, nil), // Blank VM - no simulator, no artifact, no version, no dataset
		platoConfig:      NewPlatoConfigModel(config.client),
		simSelector:      NewSimSelectorModel(config.client),
		simLaunchOptions: SimLaunchOptionsModel{}, // Will be initialized when simulator is selected
		artifactID:       ArtifactIDModel{},       // Will be initialized when simulator is selected
		quitting:         false,
	}
}

func (m Model) Init() tea.Cmd {
	return m.mainMenu.Init()
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	// Handle navigation to VM info with data
	if navMsg, ok := msg.(navigateToVMInfoMsg); ok {
		vmInfo := NewVMInfoModel(m.config.client, navMsg.sandbox, navMsg.dataset, navMsg.fromExistingSim, navMsg.artifactID, navMsg.version)
		// Mark setup as complete and set SSH info
		vmInfo.setupComplete = true
		vmInfo.sshURL = navMsg.sshURL
		vmInfo.sshHost = navMsg.sshHost
		vmInfo.sshConfigPath = navMsg.sshConfigPath
		vmInfo.sshPrivateKeyPath = navMsg.sshPrivateKeyPath
		m.vmInfo = vmInfo
		m.currentView = ViewVMInfo

		// Write .sandbox.yaml file to current working directory
		// Get path to plato-config.yml
		platoConfigPath := ""
		if configDir, err := GetPlatoConfigDir(); err == nil {
			platoConfigPath = filepath.Join(configDir, "plato-config.yml")
		}

		if err := WriteSandboxFile(navMsg.sandbox, navMsg.dataset, platoConfigPath, navMsg.artifactID, navMsg.version, navMsg.sshHost, navMsg.sshConfigPath, navMsg.sshPrivateKeyPath); err != nil {
			utils.LogDebug("Failed to write .sandbox.yaml: %v", err)
			// Non-fatal error, just log it
		} else {
			utils.LogDebug("Successfully wrote .sandbox.yaml for VM: %s", navMsg.sandbox.PublicId)
		}

		return m, m.vmInfo.Init()
	}

	// Handle navigation to proxytunnel port selector
	if navMsg, ok := msg.(navigateToProxytunnelPortMsg); ok {
		m.proxytunnelPort = NewProxytunnelPortModel(navMsg.publicID)
		m.currentView = ViewProxytunnelPort
		return m, m.proxytunnelPort.Init()
	}

	// Handle navigation to DB entry
	if navMsg, ok := msg.(navigateToDBEntryMsg); ok {
		m.dbEntry = NewDBEntryModel(navMsg.service)
		m.currentView = ViewDBEntry
		return m, m.dbEntry.Init()
	}

	// Handle opening proxytunnel with selected port
	if openMsg, ok := msg.(openTunnelMsg); ok {
		logDebug("openTunnelMsg received in main, publicID=%s, remotePort=%d", openMsg.publicID, openMsg.remotePort)
		// Open the tunnel and go back to VM info
		m.currentView = ViewVMInfo
		logDebug("Switched to ViewVMInfo and calling openProxytunnelWithPort")
		return m, openProxytunnelWithPort(m.vmInfo.client, openMsg.publicID, openMsg.remotePort)
	}

	// Handle navigation to sim launch options with simulator data
	if navMsg, ok := msg.(navigateToSimLaunchOptionsMsg); ok {
		m.simLaunchOptions = NewSimLaunchOptionsModel(m.config.client, navMsg.simulator)
		m.currentView = ViewSimLaunchOptions
		return m, m.simLaunchOptions.Init()
	}

	// Handle navigation to artifact ID with simulator data
	if navMsg, ok := msg.(navigateToArtifactIDMsg); ok {
		m.artifactID = NewArtifactIDModel(m.config.client, navMsg.simulator)
		m.currentView = ViewArtifactID
		return m, m.artifactID.Init()
	}

	// Handle environment launch with simulator and optional artifact ID
	if navMsg, ok := msg.(launchEnvironmentMsg); ok {
		m.vmConfig = NewVMConfigModel(m.config.client, navMsg.simulator, navMsg.artifactID, navMsg.version, navMsg.dataset)
		m.currentView = ViewVMConfig
		return m, m.vmConfig.Init()
	}

	// Handle launch from plato config
	if navMsg, ok := msg.(launchFromConfigMsg); ok {
		m.vmConfig = NewVMConfigModelFromConfig(m.config.client, navMsg.datasetName, navMsg.datasetConfig, navMsg.service)
		m.currentView = ViewVMConfig
		return m, m.vmConfig.Init()
	}

	// Handle navigation messages
	if navMsg, ok := msg.(NavigateMsg); ok {
		m.currentView = navMsg.view
		// Initialize the view when navigating to it
		switch navMsg.view {
		case ViewLaunchEnvironment:
			return m, m.launch.Init()
		case ViewVMConfig:
			return m, m.vmConfig.Init()
		case ViewPlatoConfig:
			return m, m.platoConfig.Init()
		case ViewSimSelector:
			return m, m.simSelector.Init()
		case ViewSimLaunchOptions:
			return m, m.simLaunchOptions.Init()
		case ViewArtifactID:
			return m, m.artifactID.Init()
		case ViewVMInfo:
			return m, m.vmInfo.Init()
		case ViewProxytunnelPort:
			return m, m.proxytunnelPort.Init()
		case ViewDBEntry:
			return m, m.dbEntry.Init()
		case ViewDatasetSelector:
			return m, m.datasetSelector.Init()
		case ViewAdvanced:
			// Initialize advanced menu with current VM info
			m.advancedMenu = NewAdvancedMenuModel(m.vmInfo.sandbox.PublicId, m.vmInfo.sshHost, m.vmInfo.sshConfigPath)
			return m, m.advancedMenu.Init()
		case ViewFlowEntry:
			return m, m.flowEntry.Init()
		}
		return m, nil
	}

	// Handle navigation to dataset selector
	if navMsg, ok := msg.(navigateToDatasetSelectorMsg); ok {
		params := snapshotParams{
			publicID:         navMsg.publicID,
			jobGroupID:       navMsg.jobGroupID,
			service:          navMsg.service,
			lastPushedBranch: navMsg.lastPushedBranch,
		}
		m.datasetSelector = NewDatasetSelectorModel(navMsg.service, params)
		m.currentView = ViewDatasetSelector
		return m, m.datasetSelector.Init()
	}

	// Handle executing advanced actions
	if actionMsg, ok := msg.(executeAdvancedActionMsg); ok {
		// Go back to VM info and execute the action
		m.currentView = ViewVMInfo

		switch actionMsg.action {
		case "Authenticate ECR":
			m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, "Authenticating Docker with AWS ECR...")
			m.vmInfo.runningCommand = true
			return m, tea.Batch(m.vmInfo.spinner.Tick, authenticateECR(m.vmInfo.sshHost, m.vmInfo.sshConfigPath))
		case "Open Proxytunnel":
			// Navigate to proxytunnel port selector
			return m, func() tea.Msg {
				return navigateToProxytunnelPortMsg{publicID: m.vmInfo.sandbox.PublicId}
			}
		case "Audit Ignore UI":
			m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, "Launching Audit Ignore UI in browser...")
			m.vmInfo.runningCommand = true
			return m, tea.Batch(m.vmInfo.spinner.Tick, launchAuditIgnoreUI())
		case "Run Flow":
			// Get public URL from sandbox and flow path from plato-config
			defaultURL := ""
			defaultFlowPath := ""

			// Use the sandbox public URL
			if m.vmInfo.sandbox != nil && m.vmInfo.sandbox.Url != "" {
				defaultURL = m.vmInfo.sandbox.Url
			}

			// Get flow path from plato-config based on current dataset
			if m.vmInfo.config != nil && m.vmInfo.dataset != "" {
				if datasetConfig, ok := m.vmInfo.config.Datasets[m.vmInfo.dataset]; ok {
					flowsPath := datasetConfig.Metadata.FlowsPath
					if flowsPath != "" {
						// Resolve path relative to plato-config.yml location
						if !filepath.IsAbs(flowsPath) {
							if configDir, err := GetPlatoConfigDir(); err == nil {
								defaultFlowPath = filepath.Join(configDir, flowsPath)
							} else {
								defaultFlowPath = flowsPath
							}
						} else {
							defaultFlowPath = flowsPath
						}
					}
				}
			}

			// Navigate to flow entry form with defaults
			m.flowEntry = NewFlowEntryModel(defaultURL, defaultFlowPath)
			m.currentView = ViewFlowEntry
			return m, m.flowEntry.Init()
		case "Get State":
			m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, "Fetching simulator state...")
			m.vmInfo.runningCommand = true
			return m, tea.Batch(m.vmInfo.spinner.Tick, getEnvironmentState(m.config.client, m.vmInfo.sandbox.JobGroupId))
		case "Set up root SSH":
			if m.vmInfo.rootPasswordSetup {
				m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, "⚠️  Root SSH password is already configured")
				return m, nil
			}
			if m.vmInfo.sshHost == "" {
				m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, "❌ SSH host not configured. Cannot set up root SSH.")
				return m, nil
			}
			m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, "Setting up root SSH password...")
			m.vmInfo.runningCommand = true
			return m, tea.Batch(m.vmInfo.spinner.Tick, setupRootPassword(m.config.client, m.vmInfo.sandbox.PublicId, m.vmInfo.sshPrivateKeyPath, m.vmInfo.sshHost))
		case "Create Checkpoint":
			// Load the config to get service
			config, err := LoadPlatoConfig()
			if err != nil {
				errMsg := fmt.Sprintf("❌ Failed to load plato-config.yml: %v", err)
				m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, errMsg)
				logErrorToFile("plato_error.log", errMsg)
				return m, nil
			}

			// Get service from config
			service := config.Service
			if service == "" {
				errMsg := "❌ Service not specified in plato-config.yml"
				m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, errMsg)
				logErrorToFile("plato_error.log", errMsg)
				return m, nil
			}

			// Use the current dataset (or nil for default)
			var dataset *string
			if m.vmInfo.dataset != "" {
				dataset = &m.vmInfo.dataset
			}

			m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, fmt.Sprintf("Creating checkpoint for service: %s...", service))
			m.vmInfo.runningCommand = true
			return m, tea.Batch(m.vmInfo.spinner.Tick, createCheckpoint(m.config.client, m.vmInfo.sandbox.PublicId, service, dataset))
		}
		return m, nil
	}

	// Handle dataset selected message - trigger snapshot with the selected dataset
	if datasetMsg, ok := msg.(datasetSelectedMsg); ok {
		logDebug("Dataset selected: %s for service: %s", datasetMsg.datasetName, datasetMsg.params.service)
		m.currentView = ViewVMInfo

		// Check if DB config exists for this service
		_, hasConfig := utils.GetDBConfig(datasetMsg.params.service)
		if !hasConfig {
			// Navigate to DB entry view
			logDebug("No DB config for service %s, navigating to DB entry", datasetMsg.params.service)
			return m, func() tea.Msg {
				return navigateToDBEntryMsg{service: datasetMsg.params.service}
			}
		}

		// DB config exists, proceed with snapshot
		datasetPtr := &datasetMsg.datasetName

		// Add status message
		m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, fmt.Sprintf("Creating snapshot for service: %s, dataset: %s", datasetMsg.params.service, datasetMsg.datasetName))
		m.vmInfo.runningCommand = true

		// Trigger snapshot
		return m, tea.Batch(
			m.vmInfo.spinner.Tick,
			createSnapshotWithCleanup(
				m.config.client,
				datasetMsg.params.publicID,
				datasetMsg.params.jobGroupID,
				datasetMsg.params.service,
				datasetPtr,
				datasetMsg.params.lastPushedBranch,
			),
		)
	}

	// Handle DB config entered message - trigger snapshot with the entered config
	if dbMsg, ok := msg.(dbConfigEnteredMsg); ok {
		logDebug("DB config entered for service: %s", dbMsg.service)
		m.currentView = ViewVMInfo

		// Get dataset pointer
		datasetPtr := &m.vmInfo.dataset

		// Trigger snapshot with the user-provided DB config
		return m, createSnapshotWithConfig(
			m.config.client,
			m.vmInfo.sandbox.PublicId,
			m.vmInfo.sandbox.JobGroupId,
			dbMsg.service,
			datasetPtr,
			dbMsg.config,
		)
	}

	// Handle flow config entered message - launch flow with user-provided config
	if flowMsg, ok := msg.(flowConfigEnteredMsg); ok {
		logDebug("Flow config entered: url=%s, flowPath=%s, flowName=%s", flowMsg.url, flowMsg.flowPath, flowMsg.flowName)
		m.currentView = ViewVMInfo

		m.vmInfo.statusMessages = append(m.vmInfo.statusMessages, fmt.Sprintf("Running flow '%s' against %s...", flowMsg.flowName, flowMsg.url))
		m.vmInfo.runningCommand = true
		return m, tea.Batch(m.vmInfo.spinner.Tick, launchRunFlow(flowMsg.url, flowMsg.flowPath, flowMsg.flowName))
	}

	// Handle global key commands
	if msg, ok := msg.(tea.KeyMsg); ok {
		k := msg.String()

		// In config, launch, vmconfig, or simselector view, esc/q goes back
		if m.currentView == ViewConfig && (k == "q" || k == "esc") {
			m.currentView = ViewMainMenu
			return m, nil
		}
		if m.currentView == ViewLaunchEnvironment && (k == "q" || k == "esc") {
			m.currentView = ViewMainMenu
			return m, nil
		}
		if m.currentView == ViewVMConfig && (k == "q" || k == "esc") {
			m.currentView = ViewLaunchEnvironment
			return m, nil
		}
		if m.currentView == ViewPlatoConfig && (k == "q" || k == "esc") {
			m.currentView = ViewLaunchEnvironment
			return m, nil
		}
		if m.currentView == ViewSimSelector && k == "q" {
			// Only handle 'q' for navigation if not filtering
			// The simSelector will handle this check
		}
		if m.currentView == ViewArtifactID && (k == "q" || k == "esc") {
			m.currentView = ViewLaunchEnvironment
			return m, nil
		}

		// In main menu, ctrl+c quits
		if m.currentView == ViewMainMenu && k == "ctrl+c" {
			m.quitting = true
			return m, tea.Quit
		}
	}

	// Route updates to current view
	var cmd tea.Cmd
	switch m.currentView {
	case ViewMainMenu:
		m.mainMenu, cmd = m.mainMenu.Update(msg)
	case ViewConfig:
		m.config, cmd = m.config.Update(msg)
	case ViewLaunchEnvironment:
		m.launch, cmd = m.launch.Update(msg)
	case ViewVMConfig:
		m.vmConfig, cmd = m.vmConfig.Update(msg)
	case ViewPlatoConfig:
		m.platoConfig, cmd = m.platoConfig.Update(msg)
	case ViewSimSelector:
		m.simSelector, cmd = m.simSelector.Update(msg)
	case ViewSimLaunchOptions:
		m.simLaunchOptions, cmd = m.simLaunchOptions.Update(msg)
	case ViewArtifactID:
		m.artifactID, cmd = m.artifactID.Update(msg)
	case ViewVMInfo:
		m.vmInfo, cmd = m.vmInfo.Update(msg)
	case ViewProxytunnelPort:
		m.proxytunnelPort, cmd = m.proxytunnelPort.Update(msg)
	case ViewDBEntry:
		m.dbEntry, cmd = m.dbEntry.Update(msg)
	case ViewDatasetSelector:
		m.datasetSelector, cmd = m.datasetSelector.Update(msg)
	case ViewAdvanced:
		m.advancedMenu, cmd = m.advancedMenu.Update(msg)
	case ViewFlowEntry:
		m.flowEntry, cmd = m.flowEntry.Update(msg)
	}

	return m, cmd
}

func (m Model) View() string {
	if m.quitting {
		return "bye!\n"
	}

	// Route view to current view
	switch m.currentView {
	case ViewMainMenu:
		return m.mainMenu.View()
	case ViewConfig:
		return m.config.View()
	case ViewLaunchEnvironment:
		return m.launch.View()
	case ViewVMConfig:
		return m.vmConfig.View()
	case ViewPlatoConfig:
		return m.platoConfig.View()
	case ViewSimSelector:
		return m.simSelector.View()
	case ViewSimLaunchOptions:
		return m.simLaunchOptions.View()
	case ViewArtifactID:
		return m.artifactID.View()
	case ViewVMInfo:
		return m.vmInfo.View()
	case ViewProxytunnelPort:
		return m.proxytunnelPort.View()
	case ViewDBEntry:
		return m.dbEntry.View()
	case ViewDatasetSelector:
		return m.datasetSelector.View()
	case ViewAdvanced:
		return m.advancedMenu.View()
	case ViewFlowEntry:
		return m.flowEntry.View()
	default:
		return "Unknown view\n"
	}
}

// showCredentials displays the user's Plato Hub credentials
func showCredentials() error {
	fmt.Println("🔑 Fetching your Plato Hub credentials...")

	// Create a config to get the client
	config := NewConfigModel()
	ctx := context.Background()

	// Get Gitea service
	giteaService := services.NewGiteaService(config.client)

	// Get credentials
	creds, err := giteaService.GetCredentials(ctx)
	if err != nil {
		return fmt.Errorf("failed to get credentials: %w", err)
	}

	fmt.Println("\n✅ Plato Hub Credentials")
	fmt.Println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	fmt.Printf("📧 Username:     %s\n", creds.Username)
	fmt.Printf("🔐 Password:     %s\n", creds.Password)
	fmt.Printf("🏢 Organization: %s\n", creds.OrgName)
	fmt.Println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	fmt.Println("\n💡 Use these credentials to:")
	fmt.Println("   • Clone repositories manually")
	fmt.Println("   • Access the Plato Hub web interface")
	fmt.Println("   • Configure Git authentication")
	fmt.Println("\n⚠️  Keep these credentials secure and do not share them")

	return nil
}

// cloneService clones a service from the Plato Hub to the local machine
func cloneService(serviceName string) error {
	fmt.Printf("🔍 Looking up service '%s' in Plato Hub...\n", serviceName)

	// Create a config to get the client
	config := NewConfigModel()
	ctx := context.Background()

	// Get Gitea service
	giteaService := services.NewGiteaService(config.client)

	// Get credentials
	fmt.Println("🔑 Fetching credentials...")
	creds, err := giteaService.GetCredentials(ctx)
	if err != nil {
		return fmt.Errorf("failed to get credentials: %w", err)
	}

	// List simulators to find the service
	fmt.Println("📋 Listing available simulators...")
	simulators, err := giteaService.ListSimulators(ctx)
	if err != nil {
		return fmt.Errorf("failed to list simulators: %w", err)
	}

	// Find the simulator by service name
	var simulator *models.GiteaSimulator
	for i := range simulators {
		if strings.EqualFold(simulators[i].Name, serviceName) {
			simulator = &simulators[i]
			break
		}
	}

	if simulator == nil {
		return fmt.Errorf("service '%s' not found in hub", serviceName)
	}

	fmt.Printf("✓ Found service: %s\n", simulator.Name)

	// Check if repository exists
	if !simulator.HasRepo {
		return fmt.Errorf("service '%s' does not have a repository yet", serviceName)
	}

	// Get repository information
	fmt.Println("📦 Fetching repository information...")
	repo, err := giteaService.GetSimulatorRepository(ctx, simulator.ID)
	if err != nil {
		return fmt.Errorf("failed to get repository: %w", err)
	}

	// Build authenticated clone URL
	cloneURL := repo.CloneURL
	if strings.HasPrefix(cloneURL, "https://") {
		cloneURL = strings.Replace(cloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
	}

	// Determine target directory (use service name)
	targetDir := simulator.Name
	if _, err := os.Stat(targetDir); err == nil {
		return fmt.Errorf("directory '%s' already exists", targetDir)
	}

	// Clone the repository
	fmt.Printf("📥 Cloning repository to '%s'...\n", targetDir)
	cmd := exec.Command("git", "clone", cloneURL, targetDir)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to clone repository: %w\nOutput: %s", err, string(output))
	}

	fmt.Printf("\n✅ Successfully cloned '%s' to '%s'\n", serviceName, targetDir)
	fmt.Printf("📂 Repository: %s\n", repo.CloneURL)
	if repo.Description != "" {
		fmt.Printf("📝 Description: %s\n", repo.Description)
	}
	fmt.Printf("\n💡 Next steps:\n")
	fmt.Printf("   cd %s\n", targetDir)
	fmt.Printf("   # Start developing!\n")

	return nil
}

func main() {
	// Handle help flag
	if len(os.Args) > 1 && (os.Args[1] == "--help" || os.Args[1] == "-h" || os.Args[1] == "help") {
		fmt.Printf("Plato CLI - Manage Plato environments and simulators\n\n")
		fmt.Printf("Usage:\n")
		fmt.Printf("  plato [command] [options]\n\n")
		fmt.Printf("Commands:\n")
		fmt.Printf("  clone <service>    Clone a service from Plato Hub to local machine\n")
		fmt.Printf("  credentials        Display your Plato Hub credentials\n")
		fmt.Printf("  --version, -v      Show version information\n")
		fmt.Printf("  --help, -h         Show this help message\n\n")
		fmt.Printf("Interactive Mode:\n")
		fmt.Printf("  Run 'plato' without any commands to start the interactive TUI\n\n")
		fmt.Printf("Examples:\n")
		fmt.Printf("  plato clone espocrm          # Clone the espocrm service\n")
		fmt.Printf("  plato credentials            # Show your Hub credentials\n")
		fmt.Printf("  plato                        # Start interactive mode\n")
		os.Exit(0)
	}

	// Handle version flag
	if len(os.Args) > 1 && (os.Args[1] == "--version" || os.Args[1] == "-v") {
		fmt.Printf("Plato CLI version %s\n", components.Version)
		fmt.Printf("Git commit: %s\n", components.GitCommit)
		fmt.Printf("Built: %s\n", components.BuildTime)
		os.Exit(0)
	}

	// Handle clone command
	if len(os.Args) > 1 && os.Args[1] == "clone" {
		if len(os.Args) < 3 {
			fmt.Println("Usage: plato clone <service>")
			fmt.Println("Example: plato clone espocrm")
			os.Exit(1)
		}
		serviceName := os.Args[2]
		if err := cloneService(serviceName); err != nil {
			fmt.Printf("Error cloning service: %v\n", err)
			os.Exit(1)
		}
		os.Exit(0)
	}

	// Handle credentials command
	if len(os.Args) > 1 && os.Args[1] == "credentials" {
		if err := showCredentials(); err != nil {
			fmt.Printf("Error fetching credentials: %v\n", err)
			os.Exit(1)
		}
		os.Exit(0)
	}

	// Initialize debug logger
	if err := utils.InitLogger(); err != nil {
		fmt.Printf("Warning: failed to initialize logger: %v\n", err)
	}

	initialModel := newModel()
	p := tea.NewProgram(initialModel)

	if _, err := p.Run(); err != nil {
		fmt.Println("could not run program:", err)
	}
}
type auditUILaunchedMsg struct {
	err error
}

func launchAuditIgnoreUI() tea.Cmd {
	return func() tea.Msg {
		// Find the script in the same directory as the binary
		exePath, err := os.Executable()
		if err != nil {
			return auditUILaunchedMsg{err: fmt.Errorf("failed to find executable: %w", err)}
		}

		scriptPath := filepath.Join(filepath.Dir(exePath), "configure_ignore_tables_ui.py")

		// Check if file exists
		if _, err := os.Stat(scriptPath); os.IsNotExist(err) {
			return auditUILaunchedMsg{err: fmt.Errorf("UI script not found at %s", scriptPath)}
		}

		// Check if uv is installed
		if _, err := exec.LookPath("uv"); err != nil {
			return auditUILaunchedMsg{err: fmt.Errorf("uv not found - install from https://docs.astral.sh/uv/")}
		}

		// Launch streamlit (uv will auto-install dependencies: streamlit, psycopg2-binary, pymysql)
		cmd := exec.Command("sh", "-c", fmt.Sprintf("uv run --with streamlit --with psycopg2-binary --with pymysql streamlit run %s &", scriptPath))
		err = cmd.Start()

		if err != nil {
			return auditUILaunchedMsg{err: fmt.Errorf("failed to launch: %w", err)}
		}

		// Open browser
		time.Sleep(2 * time.Second)
		exec.Command("open", "http://localhost:8501").Start()

		return auditUILaunchedMsg{err: nil}
	}
}

type runFlowCompletedMsg struct {
	err    error
	output string
}

type stateRetrievedMsg struct {
	state map[string]interface{}
	err   error
}

func getEnvironmentState(client *plato.PlatoClient, jobGroupID string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		state, err := client.Environment.GetState(ctx, jobGroupID, false)
		return stateRetrievedMsg{state: state, err: err}
	}
}

func launchRunFlow(url, flowPath, flowName string) tea.Cmd {
	return func() tea.Msg {
		// Find the script in the same directory as the binary
		exePath, err := os.Executable()
		if err != nil {
			return runFlowCompletedMsg{err: fmt.Errorf("failed to find executable: %w", err), output: ""}
		}

		scriptPath := filepath.Join(filepath.Dir(exePath), "run_flow.py")

		// Check if file exists
		if _, err := os.Stat(scriptPath); os.IsNotExist(err) {
			return runFlowCompletedMsg{err: fmt.Errorf("run_flow.py not found at %s", scriptPath), output: ""}
		}

		// Check if uv is installed
		if _, err := exec.LookPath("uv"); err != nil {
			return runFlowCompletedMsg{err: fmt.Errorf("uv not found - install from https://docs.astral.sh/uv/"), output: ""}
		}

		// Build command with arguments
		cmdStr := fmt.Sprintf("uv run --with playwright --with pyyaml --with pydantic python %s --url %s --flow-file %s --flow-name %s",
			scriptPath, url, flowPath, flowName)

		// Run command and capture output
		cmd := exec.Command("sh", "-c", cmdStr)
		output, err := cmd.CombinedOutput()

		if err != nil {
			return runFlowCompletedMsg{
				err:    fmt.Errorf("flow execution failed: %w", err),
				output: string(output),
			}
		}

		return runFlowCompletedMsg{err: nil, output: string(output)}
	}
}
