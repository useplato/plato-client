package main

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	plato "plato-sdk"
	"plato-sdk/models"
	"plato-sdk/services"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type EnvLauncherModel struct {
	client         *plato.PlatoClient
	simulator      *models.SimulatorListItem
	artifactID     *string
	spinner        spinner.Model
	statusMessages []string
	statusChan     chan string
	environment    *models.Environment
	err            error
	dataset        string
	sshHost        string
}

type envCreatedMsg struct {
	env *models.Environment
	err error
}

type envReadyMsg struct {
	err error
}

type envResetMsg struct {
	runSessionID string
	err          error
}

type envSSHConfiguredMsg struct {
	sshHost string
	err     error
}

type envStatusUpdateMsg struct {
	message string
}

func launchEnvironment(client *plato.PlatoClient, simulator *models.SimulatorListItem, artifactID *string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		// Step 1: Create environment
		statusChan <- fmt.Sprintf("Creating environment: %s...", simulator.Name)

		// Setup options with defaults, using "noop" interface type (no browser)
		opts := services.DefaultMakeOptions()
		opts.InterfaceType = "noop"
		opts.ArtifactID = artifactID

		env, err := client.Environment.Make(ctx, simulator.Name, opts)
		if err != nil {
			close(statusChan)
			return envCreatedMsg{env: nil, err: err}
		}

		statusChan <- fmt.Sprintf("Environment created (ID: %s)", env.JobID)
		return envCreatedMsg{env: env, err: nil}
	}
}

func waitForEnvironmentReady(client *plato.PlatoClient, jobID string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		// Wait for worker to be ready (this also indicates job is running)
		statusChan <- "Waiting for worker to be ready..."
		for {
			worker, err := client.Environment.GetWorkerReady(ctx, jobID)
			if err != nil {
				close(statusChan)
				return envReadyMsg{err: fmt.Errorf("failed to check worker status: %w", err)}
			}

			if worker.Ready {
				statusChan <- "Worker is ready"
				break
			}

			if worker.Error != nil && *worker.Error != "" {
				close(statusChan)
				return envReadyMsg{err: fmt.Errorf("worker error: %s", *worker.Error)}
			}

			time.Sleep(2 * time.Second)
		}

		return envReadyMsg{err: nil}
	}
}

func resetEnvironment(client *plato.PlatoClient, jobID string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()

		statusChan <- "Resetting environment..."
		resetResp, err := client.Environment.Reset(ctx, jobID)
		if err != nil {
			close(statusChan)
			return envResetMsg{runSessionID: "", err: err}
		}

		if !resetResp.Success {
			errMsg := "Unknown error"
			if resetResp.Error != nil {
				errMsg = *resetResp.Error
			}
			close(statusChan)
			return envResetMsg{runSessionID: "", err: fmt.Errorf("reset failed: %s", errMsg)}
		}

		statusChan <- "Environment reset complete"
		return envResetMsg{runSessionID: resetResp.Data.RunSessionID, err: nil}
	}
}

func setupSSHForEnvironment(jobID string, statusChan chan<- string) tea.Cmd {
	return func() tea.Msg {
		statusChan <- "Configuring SSH access..."

		// Choose a random port between 2200 and 2299
		localPort := rand.Intn(100) + 2200

		// Setup SSH config and get the hostname (use 'root' for existing simulator environments)
		sshHost, err := setupSSHConfig(localPort, jobID, "root")
		if err != nil {
			close(statusChan)
			return envSSHConfiguredMsg{sshHost: "", err: err}
		}

		statusChan <- fmt.Sprintf("SSH configured: ssh %s", sshHost)
		close(statusChan)
		return envSSHConfiguredMsg{sshHost: sshHost, err: nil}
	}
}

func waitForEnvStatusUpdates(statusChan <-chan string) tea.Cmd {
	return func() tea.Msg {
		select {
		case msg, ok := <-statusChan:
			if !ok {
				return envStatusUpdateMsg{message: ""}
			}
			return envStatusUpdateMsg{message: msg}
		case <-time.After(100 * time.Millisecond):
			return envStatusUpdateMsg{message: ""}
		}
	}
}

func NewEnvLauncherModel(client *plato.PlatoClient, simulator *models.SimulatorListItem, artifactID *string) EnvLauncherModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	return EnvLauncherModel{
		client:         client,
		simulator:      simulator,
		artifactID:     artifactID,
		spinner:        s,
		statusMessages: []string{},
		statusChan:     make(chan string, 10),
		dataset:        "base", // Default dataset
	}
}

func (m EnvLauncherModel) Init() tea.Cmd {
	return tea.Batch(
		m.spinner.Tick,
		launchEnvironment(m.client, m.simulator, m.artifactID, m.statusChan),
		waitForEnvStatusUpdates(m.statusChan),
	)
}

func (m EnvLauncherModel) Update(msg tea.Msg) (EnvLauncherModel, tea.Cmd) {
	switch msg := msg.(type) {
	case envStatusUpdateMsg:
		if msg.message != "" {
			m.statusMessages = append(m.statusMessages, msg.message)
		}
		// Continue listening if channel is still open
		if m.statusChan != nil {
			return m, waitForEnvStatusUpdates(m.statusChan)
		}
		return m, nil

	case envCreatedMsg:
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Failed to create environment: %v", msg.err))
			m.err = msg.err
			return m, nil
		}
		m.environment = msg.env
		return m, tea.Batch(
			waitForEnvironmentReady(m.client, msg.env.JobID, m.statusChan),
			waitForEnvStatusUpdates(m.statusChan),
		)

	case envReadyMsg:
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Environment not ready: %v", msg.err))
			m.err = msg.err
			return m, nil
		}
		return m, tea.Batch(
			resetEnvironment(m.client, m.environment.JobID, m.statusChan),
			waitForEnvStatusUpdates(m.statusChan),
		)

	case envResetMsg:
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ Reset failed: %v", msg.err))
			m.err = msg.err
			return m, nil
		}
		return m, tea.Batch(
			setupSSHForEnvironment(m.environment.JobID, m.statusChan),
			waitForEnvStatusUpdates(m.statusChan),
		)

	case envSSHConfiguredMsg:
		if msg.err != nil {
			m.statusMessages = append(m.statusMessages, fmt.Sprintf("❌ SSH config failed: %v", msg.err))
			m.err = msg.err
			return m, nil
		}
		m.sshHost = msg.sshHost
		m.statusMessages = append(m.statusMessages, "✓ Environment ready!")

		// Navigate to VM info
		return m, func() tea.Msg {
			time.Sleep(1 * time.Second)
			// Create a sandbox object for compatibility with VMInfo
			sandbox := &models.Sandbox{
				PublicID:   m.environment.JobID,
				JobGroupID: m.environment.JobID,
				URL:        getPublicURL(m.client, m.environment),
			}
			return navigateToVMInfoMsg{
				sandbox:         sandbox,
				dataset:         m.dataset,
				sshURL:          fmt.Sprintf("root@%s", m.environment.JobID),
				sshHost:         m.sshHost,
				fromExistingSim: true,
			}
		}

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	}

	return m, nil
}

func (m EnvLauncherModel) View() string {
	style := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#CCCCCC")).
		MarginLeft(2)

	statusStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#888888")).
		MarginLeft(4)

	errorStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#FF6B6B")).
		MarginLeft(4)

	var content string
	content += RenderHeader() + "\n\n"

	// Show all status messages
	for i, msg := range m.statusMessages {
		isError := strings.HasPrefix(msg, "❌")

		if i == len(m.statusMessages)-1 && m.err == nil {
			// Latest message with spinner
			if isError {
				content += errorStyle.Render(fmt.Sprintf("  %s", msg)) + "\n"
			} else {
				content += style.Render(fmt.Sprintf("  %s %s", m.spinner.View(), msg)) + "\n"
			}
		} else {
			// Previous messages
			if isError {
				content += errorStyle.Render(fmt.Sprintf("  %s", msg)) + "\n"
			} else {
				content += statusStyle.Render(fmt.Sprintf("  ✓ %s", msg)) + "\n"
			}
		}
	}

	return content
}

// getPublicURL computes the public URL for an environment based on the base URL
func getPublicURL(client *plato.PlatoClient, env *models.Environment) string {
	baseURL := client.GetBaseURL()
	identifier := env.Alias
	if identifier == "" {
		identifier = env.JobID
	}

	// Determine environment based on base_url
	if strings.Contains(baseURL, "localhost:8080") {
		return fmt.Sprintf("http://localhost:8081/%s", identifier)
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
