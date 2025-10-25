// Package main provides the Plato CLI application.
//
// This is the main entry point for the Plato CLI tool, which provides an interactive
// terminal UI for managing Plato simulators, environments, and sandboxes. The CLI
// uses the Bubble Tea framework to provide a view-based navigation system with
// multiple screens including main menu, configuration, simulator selection,
// environment launching, and VM management.
package main

import (
	"fmt"
	"os"

	"plato-sdk/models"

	tea "github.com/charmbracelet/bubbletea"
)

type ViewState int

type NavigateMsg struct {
	view ViewState
}

type navigateToVMInfoMsg struct {
	sandbox         *models.Sandbox
	dataset         string
	sshURL          string
	sshHost         string
	fromExistingSim bool
	artifactID      *string
	version         *string
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
		m.vmInfo = vmInfo
		m.currentView = ViewVMInfo
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
		return m, openProxytunnelWithPort(openMsg.publicID, openMsg.remotePort)
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

	// Handle dataset selected message - trigger snapshot with the selected dataset
	if datasetMsg, ok := msg.(datasetSelectedMsg); ok {
		logDebug("Dataset selected: %s for service: %s", datasetMsg.datasetName, datasetMsg.params.service)
		m.currentView = ViewVMInfo

		// Check if DB config exists for this service
		_, hasConfig := getDBConfig(datasetMsg.params.service)
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
			m.vmInfo.sandbox.PublicID,
			m.vmInfo.sandbox.JobGroupID,
			dbMsg.service,
			datasetPtr,
			dbMsg.config,
		)
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
	default:
		return "Unknown view\n"
	}
}

func main() {
	// Handle version flag
	if len(os.Args) > 1 && (os.Args[1] == "--version" || os.Args[1] == "-v") {
		fmt.Printf("Plato CLI version %s\n", version)
		fmt.Printf("Git commit: %s\n", gitCommit)
		fmt.Printf("Built: %s\n", buildTime)
		os.Exit(0)
	}

	// Initialize debug logger
	if err := initLogger(); err != nil {
		fmt.Printf("Warning: failed to initialize logger: %v\n", err)
	}

	initialModel := newModel()
	p := tea.NewProgram(initialModel)

	if _, err := p.Run(); err != nil {
		fmt.Println("could not run program:", err)
	}
}
