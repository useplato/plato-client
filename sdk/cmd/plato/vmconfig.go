// Package main provides the VM configuration view for the Plato CLI.
//
// This file implements the VMConfigModel which handles configuring and creating
// VM sandboxes. It presents a form for users to specify VM parameters like alias,
// dataset, and resource requirements, then orchestrates the VM creation and setup
// process including monitoring via SSE events.
package main

import (
	"context"
	"fmt"
	"math/rand"
	"os"
	plato "plato-sdk"
	"plato-sdk/cmd/plato/internal/ui/components"
	"plato-sdk/cmd/plato/internal/utils"
	"plato-sdk/models"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
)

type VMConfigModel struct {
	client         *plato.PlatoClient
	simulator      *models.SimulatorListItem // Optional: for launching from existing sim
	artifactID     *string                   // Optional: for launching with artifact
	version        *string                   // Optional: version string for the artifact
	service        string                    // Service name from config
	form           *huh.Form
	lg             *lipgloss.Renderer
	creating       bool
	settingUp      bool
	started        bool // Track if we've started the creation process
	width          int
	err            error
	spinner        spinner.Model
	stopwatch      components.Stopwatch
	statusMessages []string
	statusChan     chan string
	sandbox        *models.Sandbox
	dataset        string
	datasetConfig  models.SimConfigDataset
	sshURL         string
	sshHost        string
	sshConfigPath  string
	skipForm       bool // Skip form and use defaults when launching from simulator
}

var (
	vmMagenta = lipgloss.AdaptiveColor{Light: "#FF06B7", Dark: "#FF06B7"}
)

type sandboxCreatedMsg struct {
	sandbox *models.Sandbox
	err     error
}

type sandboxSetupCompleteMsg struct {
	sshURL        string
	sshHost       string
	sshConfigPath string
	err           error
}

type statusUpdateMsg struct {
	message string
}

func createSandbox(client *plato.PlatoClient, config models.SimConfigDataset, dataset string, statusChan chan<- string, artifactID *string, service string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		// Create the sandbox
		statusChan <- "Creating VM via API..."
		// Use simulator name as alias if available in metadata, otherwise "sandbox"
		alias := "sandbox"
		if config.Metadata.Name != "" && config.Metadata.Name != "Plato Simulator" {
			alias = config.Metadata.Name
		}

		sandbox, err := client.Sandbox.Create(ctx, config, dataset, alias, artifactID, service)
		if err != nil {
			close(statusChan)
			return sandboxCreatedMsg{sandbox: nil, err: err}
		}

		statusChan <- fmt.Sprintf("VM created (ID: %s)", sandbox.PublicID)
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

func setupSSHForArtifact(client *plato.PlatoClient, sandbox *models.Sandbox, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		statusChan <- "Configuring SSH access..."

		// Choose a random port between 2200 and 2299
		localPort := rand.Intn(100) + 2200

		// Setup SSH config using PublicID with 'plato' user (not root)
		sshHost, configPath, err := utils.SetupSSHConfig(client.GetBaseURL(), localPort, sandbox.PublicID, "plato")
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:        "",
				sshHost:       "",
				sshConfigPath: "",
				err:           fmt.Errorf("SSH config setup failed: %w", err),
			}
		}

		statusChan <- fmt.Sprintf("SSH configured: ssh -F %s %s", configPath, sshHost)

		// Generate SSH connection info
		sshURL := fmt.Sprintf("plato@%s", sandbox.PublicID)

		statusChan <- "✓ VM ready!"
		close(statusChan)

		return sandboxSetupCompleteMsg{
			sshURL:        sshURL,
			sshHost:       sshHost,
			sshConfigPath: configPath,
			err:           nil,
		}
	}
}

func setupSandboxFromConfig(client *plato.PlatoClient, sandbox *models.Sandbox, config models.SimConfigDataset, dataset string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		statusChan <- "Setting up sandbox environment..."

		// Read SSH public key for plato user
		statusChan <- "Reading SSH public key..."
		sshPublicKey, err := utils.ReadSSHPublicKey()
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:        "",
				sshHost:       "",
				sshConfigPath: "",
				err:           fmt.Errorf("failed to read SSH public key: %w", err),
			}
		}

		statusChan <- "Calling setup-sandbox API..."

		// Call the setup-sandbox API with full config and SSH public key
		correlationID, err := client.Sandbox.SetupSandbox(ctx, sandbox.PublicID, config, dataset, sshPublicKey)
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:        "",
				sshHost:       "",
				sshConfigPath: "",
				err:           err,
			}
		}

		statusChan <- "Monitoring sandbox setup..."

		// Monitor the setup operation via SSE using the returned correlation_id
		// Pass statusChan to get real-time event details
		err = client.Sandbox.MonitorOperationWithEvents(ctx, correlationID, 20*time.Minute, statusChan)
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:        "",
				sshHost:       "",
				sshConfigPath: "",
				err:           fmt.Errorf("setup monitoring failed: %w", err),
			}
		}

		statusChan <- "Configuring SSH access..."

		// Choose a random port between 2200 and 2299
		localPort := rand.Intn(100) + 2200

		// Setup SSH config and get the hostname (use 'plato' user for blank VMs)
		sshHost, configPath, err := utils.SetupSSHConfig(client.GetBaseURL(), localPort, sandbox.PublicID, "plato")
		if err != nil {
			close(statusChan)
			return sandboxSetupCompleteMsg{
				sshURL:        "",
				sshHost:       "",
				sshConfigPath: "",
				err:           fmt.Errorf("SSH config setup failed: %w", err),
			}
		}

		// Inform user how to connect
		statusChan <- fmt.Sprintf("SSH configured: ssh -F %s %s", configPath, sshHost)

		// Generate SSH connection info
		sshURL := fmt.Sprintf("root@%s", sandbox.PublicID)

		close(statusChan)

		return sandboxSetupCompleteMsg{
			sshURL:        sshURL,
			sshHost:       sshHost,
			sshConfigPath: configPath,
			err:           nil,
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

func NewVMConfigModelFromConfig(client *plato.PlatoClient, datasetName string, datasetConfig models.SimConfigDataset, service string) VMConfigModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	m := VMConfigModel{
		client:         client,
		simulator:      nil,
		artifactID:     nil,
		version:        nil,
		service:        service,
		width:          80,
		spinner:        s,
		stopwatch:      components.NewStopwatch(),
		statusMessages: []string{fmt.Sprintf("Starting VM creation for dataset: %s...", datasetName)},
		skipForm:       true,
		dataset:        datasetName,
		datasetConfig:  datasetConfig,
		creating:       true,
		started:        true,
		statusChan:     make(chan string, 10),
	}
	m.lg = lipgloss.DefaultRenderer()

	theme := huh.ThemeCharm()
	theme.Focused.Base = theme.Focused.Base.BorderForeground(vmMagenta)
	theme.Focused.Title = theme.Focused.Title.Foreground(vmMagenta)
	theme.Focused.TextInput.Cursor = theme.Focused.TextInput.Cursor.Foreground(vmMagenta)
	theme.Focused.TextInput.Prompt = theme.Focused.TextInput.Prompt.Foreground(vmMagenta)

	m.form = huh.NewForm()
	m.form.WithTheme(theme)

	return m
}

func NewVMConfigModel(client *plato.PlatoClient, simulator *models.SimulatorListItem, artifactID *string, version *string, dataset *string) VMConfigModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	// Skip form if simulator is provided
	skipForm := simulator != nil

	// Use provided dataset or default to "base"
	datasetValue := "base"
	if dataset != nil {
		datasetValue = *dataset
	}

	m := VMConfigModel{
		client:         client,
		simulator:      simulator,
		artifactID:     artifactID,
		version:        version,
		width:          80,
		spinner:        s,
		stopwatch:      components.NewStopwatch(),
		statusMessages: []string{},
		skipForm:       skipForm,
		dataset:        datasetValue,
	}
	m.lg = lipgloss.DefaultRenderer()

	// If skipping form, set up for immediate creation
	if skipForm {
		m.creating = true
		m.started = true
		m.statusMessages = []string{fmt.Sprintf("Starting VM creation for %s...", simulator.Name)}
		m.statusChan = make(chan string, 10)
		m.datasetConfig = m.buildConfig(1, 512, 10240)
	}

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

			huh.NewInput().
				Key("service").
				Title("Service Name").
				Description("Name of the service (e.g., my-app, api-service)").
				Placeholder("my-service"),

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
	// If skipping form (launching from simulator), immediately start creation
	if m.skipForm {
		return tea.Batch(
			m.spinner.Tick,
			m.stopwatch.Start(),
			createSandbox(m.client, m.datasetConfig, m.dataset, m.statusChan, m.artifactID, m.service),
			waitForStatusUpdates(m.statusChan),
		)
	}
	return m.form.Init()
}

// buildConfig creates a SimConfigDataset with the given parameters
func (m VMConfigModel) buildConfig(cpu, memory, disk int) models.SimConfigDataset {
	var name, description string
	if m.simulator != nil {
		name = m.simulator.Name
		if m.simulator.Description != nil {
			description = *m.simulator.Description
		}
	} else {
		name = "Plato Simulator"
		description = "A Plato simulator environment"
	}

	compute := models.SimConfigCompute{
		CPUs:               cpu,
		Memory:             memory,
		Disk:               disk,
		AppPort:            8080,
		PlatoMessagingPort: 7000,
	}

	metadata := models.SimConfigMetadata{
		Favicon:       "https://plato.so/favicon.ico",
		Name:          name,
		Description:   description,
		SourceCodeURL: "https://github.com/useplato/plato",
		StartURL:      "http://localhost:8080",
		License:       "MIT",
		Variables:     []map[string]string{{"name": "PLATO_API_KEY", "value": "your-api-key"}},
	}

	return models.SimConfigDataset{
		Compute:   compute,
		Metadata:  metadata,
		Services:  map[string]*models.SimConfigService{},
		Listeners: map[string]*models.SimConfigListener{},
	}
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
			return m, m.stopwatch.Stop()
		}
		// Don't add another success message - SSE events already showed completion
		m.sandbox = msg.sandbox

		// If artifact ID is present, skip sandbox setup and just configure SSH (without root password)
		if m.artifactID != nil {
			m.settingUp = true
			m.statusChan = make(chan string, 10)
			return m, tea.Batch(
				setupSSHForArtifact(m.client, msg.sandbox, m.statusChan),
				waitForStatusUpdates(m.statusChan),
			)
		}

		// For blank VMs, run full sandbox setup
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
			// write error to file
			errFile, err := os.Create("setup_error.txt")
			if err != nil {
				fmt.Println("Error creating error file:", err)
			}
			defer errFile.Close()
			errFile.WriteString(fmt.Sprintf("Sandbox setup failed: %v", msg.err))
			return m, m.stopwatch.Stop()
		}
		m.statusMessages = append(m.statusMessages, fmt.Sprintf("✓ Sandbox setup complete! (took %s)", m.stopwatch.View()))

		m.sshURL = msg.sshURL
		m.sshHost = msg.sshHost
		m.sshConfigPath = msg.sshConfigPath

		// Wait a moment to show success, then navigate to VM info view
		return m, tea.Batch(
			m.stopwatch.Stop(),
			func() tea.Msg {
				time.Sleep(1 * time.Second)
				return navigateToVMInfoMsg{
					sandbox:         m.sandbox,
					dataset:         m.dataset,
					sshURL:          msg.sshURL,
					sshHost:         msg.sshHost,
					sshConfigPath:   msg.sshConfigPath,
					fromExistingSim: m.artifactID != nil, // True if launched with artifact ID
					artifactID:      m.artifactID,
					version:         m.version,
				}
			},
		)

	case TickMsg, StartStopMsg, ResetMsg:
		// Handle stopwatch messages
		var cmd tea.Cmd
		m.stopwatch, cmd = m.stopwatch.Update(msg)
		return m, cmd

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

	// Only process the form if we're not skipping it
	if !m.skipForm {
		form, cmd := m.form.Update(msg)
		if f, ok := form.(*huh.Form); ok {
			m.form = f
			cmds = append(cmds, cmd)
		}
	}

	// When form is completed, create the sandbox (but only if we haven't started yet)
	// Only check form state if we're not skipping the form
	if !m.skipForm && m.form.State == huh.StateCompleted && !m.creating && !m.started {
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
		serviceVal := m.form.GetString("service")
		if serviceVal == "" {
			serviceVal = "my-service"
		}

		cpu, _ := strconv.Atoi(cpuVal)
		memory, _ := strconv.Atoi(memVal)
		disk, _ := strconv.Atoi(diskVal)

		// Build SimConfigDataset using helper method
		datasetConfig := m.buildConfig(cpu, memory, disk)

		// Save config if requested
		saveConfig := m.form.GetBool("save_config")
		if saveConfig {
			config := models.DefaultPlatoConfig(datasetVal)
			// Set the service name
			config.Service = serviceVal
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
		cmds = append(cmds, m.stopwatch.Start())
		cmds = append(cmds, createSandbox(m.client, datasetConfig, datasetVal, m.statusChan, nil, m.service))
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
			Width(m.width - 8). // Allow wrapping with margin
			MaxWidth(m.width - 8)

		// Show elapsed time if stopwatch is running
		if m.stopwatch.Running() {
			timeStyle := lipgloss.NewStyle().
				Foreground(lipgloss.Color("#7D56F4")).
				MarginLeft(2).
				Bold(true)
			content += timeStyle.Render(fmt.Sprintf("  ⏱  %s elapsed", m.stopwatch.View())) + "\n\n"
		}

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

		return components.RenderHeader() + content
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

	return components.RenderHeader() + "\n" + header + "\n" + baseStyle.Render(form)
}
