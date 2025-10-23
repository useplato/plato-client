package main

import (
	"context"
	"fmt"
	"math/rand"
	"strconv"
	"strings"
	"time"

	plato "plato-sdk"
	"plato-sdk/models"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
)

type VMConfigModel struct {
	client         *plato.PlatoClient
	form           *huh.Form
	lg             *lipgloss.Renderer
	creating       bool
	settingUp      bool
	started        bool // Track if we've started the creation process
	width          int
	err            error
	spinner        spinner.Model
	statusMessages []string
	statusChan     chan string
	sandbox        *models.Sandbox
	dataset        string
	datasetConfig  models.SimConfigDataset
	sshURL         string
	sshHost        string
}

var (
	vmMagenta = lipgloss.AdaptiveColor{Light: "#FF06B7", Dark: "#FF06B7"}
)

type sandboxCreatedMsg struct {
	sandbox *models.Sandbox
	err     error
}

type sandboxSetupCompleteMsg struct {
	sshURL  string
	sshHost string
	err     error
}

type statusUpdateMsg struct {
	message string
}

func createSandbox(client *plato.PlatoClient, config models.SimConfigDataset, dataset string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		// Create the sandbox
		statusChan <- "Creating VM via API..."
		sandbox, err := client.Sandbox.Create(ctx, config, dataset, "sandbox", nil)
		if err != nil {
			close(statusChan)
			return sandboxCreatedMsg{sandbox: nil, err: err}
		}

		statusChan <- fmt.Sprintf("VM created (ID: %s)", sandbox.PublicID[:8])
		statusChan <- "Monitoring VM provisioning..."

		// Monitor the operation until completion using the correlation_id from the API
		// Pass statusChan to get real-time event details
		err = client.Sandbox.MonitorOperationWithEvents(ctx, sandbox.CorrelationID, 20*time.Minute, statusChan)
		if err != nil {
			return sandboxCreatedMsg{sandbox: sandbox, err: fmt.Errorf("VM provisioning failed: %w", err)}
		}

		// Don't send another success message here - MonitorOperation already sent events
		// Don't close statusChan here - we'll reuse it for setup
		return sandboxCreatedMsg{sandbox: sandbox, err: nil}
	}
}

func setupSandboxFromConfig(client *plato.PlatoClient, sandbox *models.Sandbox, config models.SimConfigDataset, dataset string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		statusChan <- "Setting up sandbox environment..."

		statusChan <- "Calling setup-sandbox API..."

		// Call the setup-sandbox API with full config
		correlationID, err := client.Sandbox.SetupSandbox(ctx, sandbox.PublicID, config, dataset)
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:  "",
				sshHost: "",
				err:     err,
			}
		}

		statusChan <- "Monitoring sandbox setup..."

		// Monitor the setup operation via SSE using the returned correlation_id
		// Pass statusChan to get real-time event details
		err = client.Sandbox.MonitorOperationWithEvents(ctx, correlationID, 20*time.Minute, statusChan)
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:  "",
				sshHost: "",
				err:     fmt.Errorf("setup monitoring failed: %w", err),
			}
		}

		statusChan <- "Configuring SSH access..."

		// Choose a random port between 2200 and 2299
		localPort := rand.Intn(100) + 2200

		// Setup SSH config and get the hostname
		sshHost, err := setupSSHConfig(localPort, sandbox.JobGroupID)
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:  "",
				sshHost: "",
				err:     fmt.Errorf("SSH config setup failed: %w", err),
			}
		}

		// Generate SSH connection info
		sshURL := fmt.Sprintf("root@%s", sandbox.JobGroupID)

		statusChan <- fmt.Sprintf("SSH configured: ssh %s", sshHost)
		close(statusChan)

		return sandboxSetupCompleteMsg{
			sshURL:  sshURL,
			sshHost: sshHost,
			err:     nil,
		}
	}
}

func waitForStatusUpdates(statusChan <-chan string) tea.Cmd {
	return func() tea.Msg {
		select {
		case msg, ok := <-statusChan:
			if !ok {
				// Channel closed, no more updates
				return statusUpdateMsg{message: ""}
			}
			return statusUpdateMsg{message: msg}
		case <-time.After(100 * time.Millisecond):
			// Timeout, keep waiting
			return statusUpdateMsg{message: ""}
		}
	}
}

func listenForStatusUpdates() tea.Cmd {
	return func() tea.Msg {
		time.Sleep(100 * time.Millisecond)
		return statusUpdateMsg{message: "Submitting VM creation request..."}
	}
}

func NewVMConfigModel(client *plato.PlatoClient) VMConfigModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	m := VMConfigModel{
		client:         client,
		width:          80,
		spinner:        s,
		statusMessages: []string{},
	}
	m.lg = lipgloss.DefaultRenderer()

	theme := huh.ThemeCharm()
	theme.Focused.Base = theme.Focused.Base.BorderForeground(vmMagenta)
	theme.Focused.Title = theme.Focused.Title.Foreground(vmMagenta)
	theme.Focused.TextInput.Cursor = theme.Focused.TextInput.Cursor.Foreground(vmMagenta)
	theme.Focused.TextInput.Prompt = theme.Focused.TextInput.Prompt.Foreground(vmMagenta)

	// Default values as pointers
	defaultCPU := "1"
	defaultMemory := "512"
	defaultDisk := "10240"

	m.form = huh.NewForm(
		huh.NewGroup(
			huh.NewInput().
				Key("cpu").
				Title("CPU Count").
				Description("Number of virtual CPU cores (1-2)").
				Value(&defaultCPU).
				Validate(func(s string) error {
					if s == "" {
						return nil
					}
					cpu, err := strconv.Atoi(s)
					if err != nil {
						return fmt.Errorf("must be a number")
					}
					if cpu <= 0 || cpu > 2 {
						return fmt.Errorf("must be between 1-2")
					}
					return nil
				}),

			huh.NewInput().
				Key("memory").
				Title("Memory (MB)").
				Description("Amount of RAM in megabytes (128-4096)").
				Value(&defaultMemory).
				Validate(func(s string) error {
					if s == "" {
						return nil
					}
					mem, err := strconv.Atoi(s)
					if err != nil {
						return fmt.Errorf("must be a number")
					}
					if mem < 128 || mem > 4096 {
						return fmt.Errorf("must be between 128-4096")
					}
					return nil
				}),

			huh.NewInput().
				Key("disk").
				Title("Disk Space (MB)").
				Description("Amount of disk space in megabytes (1024-102400)").
				Value(&defaultDisk).
				Validate(func(s string) error {
					if s == "" {
						return nil
					}
					disk, err := strconv.Atoi(s)
					if err != nil {
						return fmt.Errorf("must be a number")
					}
					if disk < 1024 || disk > 102400 {
						return fmt.Errorf("must be between 1024-102400")
					}
					return nil
				}),

			huh.NewInput().
				Key("dataset").
				Title("Dataset Name").
				Description("Name for the dataset in plato-config.yml").
				Placeholder("base"),

			huh.NewConfirm().
				Key("save_config").
				Title("Save Configuration").
				Description("Save this configuration to plato-config.yml?").
				Affirmative("Yes").
				Negative("No"),

			huh.NewConfirm().
				Key("submit").
				Title("Create VM").
				Description("Press enter to create the virtual machine").
				Affirmative("Create!").
				Negative(""),
		),
	).
		WithWidth(50).
		WithShowHelp(true).
		WithShowErrors(true).
		WithTheme(theme)

	return m
}

func (m VMConfigModel) Init() tea.Cmd {
	return m.form.Init()
}

func (m VMConfigModel) Update(msg tea.Msg) (VMConfigModel, tea.Cmd) {
	switch msg := msg.(type) {
	case statusUpdateMsg:
		if msg.message != "" {
			m.statusMessages = append(m.statusMessages, msg.message)
		}
		// Continue listening for more status updates if still creating or setting up
		if (m.creating || m.settingUp) && m.statusChan != nil {
			return m, waitForStatusUpdates(m.statusChan)
		}
		// If channel is closed and we're done, stop creating/setting up
		if !m.creating && !m.settingUp {
			return m, nil
		}
		return m, nil

	case sandboxCreatedMsg:
		m.creating = false
		if msg.err != nil {
			// Show error inline with other status messages instead of switching to error view
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ VM provisioning failed: %v", msg.err))
			return m, nil
		}
		// Don't add another success message - SSE events already showed completion
		m.sandbox = msg.sandbox

		// Automatically start sandbox setup
		m.settingUp = true
		m.statusChan = make(chan string, 10)
		return m, tea.Batch(
			setupSandboxFromConfig(m.client, msg.sandbox, m.datasetConfig, m.dataset, m.statusChan),
			waitForStatusUpdates(m.statusChan),
		)

	case sandboxSetupCompleteMsg:
		m.settingUp = false
		if msg.err != nil {
			// Show error inline with other status messages instead of switching to error view
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Sandbox setup failed: %v", msg.err))
			return m, nil
		}
		m.statusMessages = append(m.statusMessages, "✓ Sandbox setup complete!")
		m.sshURL = msg.sshURL
		m.sshHost = msg.sshHost

		// Wait a moment to show success, then navigate to VM info view
		return m, func() tea.Msg {
			time.Sleep(1 * time.Second)
			return navigateToVMInfoMsg{
				sandbox: m.sandbox,
				dataset: m.dataset,
				sshURL:  msg.sshURL,
				sshHost: msg.sshHost,
			}
		}

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.WindowSizeMsg:
		m.width = msg.Width

	case tea.KeyMsg:
		switch msg.String() {
		case "esc":
			// If there's an error, clear it and allow retry
			if m.err != nil {
				m.err = nil
				m.creating = false
				return m, nil
			}
			if m.form.State == huh.StateNormal {
				return m, func() tea.Msg {
					return NavigateMsg{view: ViewLaunchEnvironment}
				}
			}
		}
	}

	var cmds []tea.Cmd

	// Process the form
	form, cmd := m.form.Update(msg)
	if f, ok := form.(*huh.Form); ok {
		m.form = f
		cmds = append(cmds, cmd)
	}

	// When form is completed, create the sandbox (but only if we haven't started yet)
	if m.form.State == huh.StateCompleted && !m.creating && !m.started {
		cpuVal := m.form.GetString("cpu")
		if cpuVal == "" {
			cpuVal = "1"
		}
		memVal := m.form.GetString("memory")
		if memVal == "" {
			memVal = "512"
		}
		diskVal := m.form.GetString("disk")
		if diskVal == "" {
			diskVal = "10240"
		}
		datasetVal := m.form.GetString("dataset")
		if datasetVal == "" {
			datasetVal = "base"
		}

		cpu, _ := strconv.Atoi(cpuVal)
		memory, _ := strconv.Atoi(memVal)
		disk, _ := strconv.Atoi(diskVal)

		// Build SimConfigDataset
		compute := models.SimConfigCompute{
			CPUs:               cpu,
			Memory:             memory,
			Disk:               disk,
			AppPort:            8080,
			PlatoMessagingPort: 7000,
		}

		metadata := models.SimConfigMetadata{
			Favicon:       "https://plato.so/favicon.ico",
			Name:          "Plato Simulator",
			Description:   "A Plato simulator environment",
			SourceCodeURL: "https://github.com/useplato/plato",
			StartURL:      "http://localhost:8080",
			License:       "MIT",
			Variables:     []map[string]string{{"name": "PLATO_API_KEY", "value": "your-api-key"}},
		}

		datasetConfig := models.SimConfigDataset{
			Compute:   compute,
			Metadata:  metadata,
			Services:  map[string]*models.SimConfigService{},
			Listeners: map[string]*models.SimConfigListener{},
		}

		// Save config if requested
		saveConfig := m.form.GetBool("save_config")
		if saveConfig {
			config := models.DefaultPlatoConfig(datasetVal)
			// Update compute values by recreating the dataset
			dataset := config.Datasets[datasetVal]
			dataset.Compute.CPUs = cpu
			dataset.Compute.Memory = memory
			dataset.Compute.Disk = disk
			config.Datasets[datasetVal] = dataset
			if err := SavePlatoConfig(config); err != nil {
				// Non-fatal: just continue without saving
				// Could add error handling here if needed
			}
		}

		m.creating = true
		m.started = true
		m.dataset = datasetVal
		m.datasetConfig = datasetConfig // Store the config for later use in setup
		m.statusMessages = []string{"Starting VM creation..."}
		m.statusChan = make(chan string, 10)

		cmds = append(cmds, m.spinner.Tick)
		cmds = append(cmds, createSandbox(m.client, datasetConfig, datasetVal, m.statusChan))
		cmds = append(cmds, waitForStatusUpdates(m.statusChan))
	}

	return m, tea.Batch(cmds...)
}

func (m VMConfigModel) View() string {
	// Once we've started, always show the status view (even after errors)
	if m.started {
		style := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#CCCCCC")).
			MarginLeft(2)

		statusStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#888888")).
			MarginLeft(4)

		var content string
		content += "\n"

		errorStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF6B6B")).
			MarginLeft(4).
			Width(m.width - 8) // Allow wrapping with margin

		// Show all status messages with spinner on the latest one
		for i, msg := range m.statusMessages {
			// Check if this is an error message
			isError := strings.HasPrefix(msg, "❌")

			if i == len(m.statusMessages)-1 {
				// Latest message with spinner
				if isError {
					// Wrap error messages to prevent truncation
					content += errorStyle.Render(fmt.Sprintf("  %s", msg)) + "\n"
				} else {
					content += style.Render(fmt.Sprintf("  %s %s", m.spinner.View(), msg)) + "\n"
				}
			} else {
				// Previous messages
				if isError {
					// Show errors without checkmark with wrapping
					content += errorStyle.Render(fmt.Sprintf("  %s", msg)) + "\n"
				} else {
					content += statusStyle.Render(fmt.Sprintf("  ✓ %s", msg)) + "\n"
				}
			}
		}

		return RenderHeader() + content
	}

	headerStyle := lipgloss.NewStyle().
		Foreground(vmMagenta).
		Bold(true).
		MarginLeft(2).
		MarginTop(1).
		MarginBottom(1)

	baseStyle := lipgloss.NewStyle().
		MarginLeft(2)

	header := headerStyle.Render("Configure Virtual Machine")
	form := m.form.View()

	return RenderHeader() + "\n" + header + "\n" + baseStyle.Render(form)
}
