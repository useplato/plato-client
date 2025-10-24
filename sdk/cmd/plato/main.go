package main

import (
	"fmt"

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
	ViewEnvLauncher
	ViewVMInfo
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
	envLauncher      EnvLauncherModel
	vmInfo           VMInfoModel
	quitting         bool
}

func newModel() Model {
	config := NewConfigModel()
	return Model{
		currentView:      ViewMainMenu,
		mainMenu:         NewMainMenuModel(),
		config:           config,
		launch:           NewLaunchModel(config.client),
		vmConfig:         NewVMConfigModel(config.client),
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
		vmInfo := NewVMInfoModel(m.config.client, navMsg.sandbox, navMsg.dataset, navMsg.fromExistingSim)
		// Mark setup as complete and set SSH info
		vmInfo.setupComplete = true
		vmInfo.sshURL = navMsg.sshURL
		vmInfo.sshHost = navMsg.sshHost
		m.vmInfo = vmInfo
		m.currentView = ViewVMInfo
		return m, m.vmInfo.Init()
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
		m.envLauncher = NewEnvLauncherModel(m.config.client, navMsg.simulator, navMsg.artifactID)
		m.currentView = ViewEnvLauncher
		return m, m.envLauncher.Init()
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
		}
		return m, nil
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
	case ViewEnvLauncher:
		m.envLauncher, cmd = m.envLauncher.Update(msg)
	case ViewVMInfo:
		m.vmInfo, cmd = m.vmInfo.Update(msg)
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
	case ViewEnvLauncher:
		return m.envLauncher.View()
	case ViewVMInfo:
		return m.vmInfo.View()
	default:
		return "Unknown view\n"
	}
}

func main() {
	initialModel := newModel()
	p := tea.NewProgram(initialModel)

	if _, err := p.Run(); err != nil {
		fmt.Println("could not run program:", err)
	}
}
