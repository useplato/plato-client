// Package services provides the Gitea service for Plato API operations.
//
// This file implements the GiteaService which handles Gitea integration operations
// including retrieving authentication credentials, listing simulators with repository
// information, and managing simulator repositories. Gitea is the git hosting platform
// used by Plato for storing and versioning simulator source code.
package services

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"plato-sdk/models"
	"plato-sdk/utils"
)

// GiteaService handles Gitea-related API operations
type GiteaService struct {
	client ClientInterface
}

// NewGiteaService creates a new Gitea service
func NewGiteaService(client ClientInterface) *GiteaService {
	return &GiteaService{client: client}
}

// GetCredentials retrieves Gitea credentials for the organization
func (s *GiteaService) GetCredentials(ctx context.Context) (*models.GiteaCredentials, error) {
	req, err := s.client.NewHubRequest(ctx, "GET", "/gitea/credentials", nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var creds models.GiteaCredentials
	if err := json.NewDecoder(resp.Body).Decode(&creds); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &creds, nil
}

// ListSimulators lists all simulators with Gitea repository information
func (s *GiteaService) ListSimulators(ctx context.Context) ([]models.GiteaSimulator, error) {
	req, err := s.client.NewHubRequest(ctx, "GET", "/gitea/simulators", nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var simulators []models.GiteaSimulator
	if err := json.NewDecoder(resp.Body).Decode(&simulators); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return simulators, nil
}

// GetSimulatorRepository retrieves repository information for a simulator
func (s *GiteaService) GetSimulatorRepository(ctx context.Context, simulatorID int) (*models.GiteaRepository, error) {
	req, err := s.client.NewHubRequest(ctx, "GET", fmt.Sprintf("/gitea/simulators/%d/repo", simulatorID), nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var repo models.GiteaRepository
	if err := json.NewDecoder(resp.Body).Decode(&repo); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &repo, nil
}

// CreateSimulatorRepository creates a repository for a simulator
func (s *GiteaService) CreateSimulatorRepository(ctx context.Context, simulatorID int) (*models.GiteaRepository, error) {
	req, err := s.client.NewHubRequest(ctx, "POST", fmt.Sprintf("/gitea/simulators/%d/repo", simulatorID), nil)
	if err != nil {
		return nil, err
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var repo models.GiteaRepository
	if err := json.NewDecoder(resp.Body).Decode(&repo); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &repo, nil
}

// PushResult contains information about a successful push to Gitea
type PushResult struct {
	RepoURL    string
	CloneCmd   string
	BranchName string
	GitHash    string
}

// PushToHub pushes local code to a Gitea repository on a timestamped branch
func (s *GiteaService) PushToHub(ctx context.Context, serviceName string, sourceDir string) (*PushResult, error) {
	if sourceDir == "" {
		var err error
		sourceDir, err = os.Getwd()
		if err != nil {
			return nil, fmt.Errorf("failed to get current directory: %w", err)
		}
	}

	// Get Gitea credentials
	creds, err := s.GetCredentials(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get credentials: %w", err)
	}

	// Find simulator by service name
	simulators, err := s.ListSimulators(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to list simulators: %w", err)
	}

	var simulator *models.GiteaSimulator
	for i := range simulators {
		if strings.EqualFold(simulators[i].Name, serviceName) {
			simulator = &simulators[i]
			break
		}
	}

	if simulator == nil {
		return nil, fmt.Errorf("simulator '%s' not found in hub", serviceName)
	}

	// Get or create repository
	var repo *models.GiteaRepository
	if simulator.HasRepo {
		repo, err = s.GetSimulatorRepository(ctx, simulator.ID)
		if err != nil {
			return nil, fmt.Errorf("failed to get repository: %w", err)
		}
	} else {
		repo, err = s.CreateSimulatorRepository(ctx, simulator.ID)
		if err != nil {
			return nil, fmt.Errorf("failed to create repository: %w", err)
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
		return nil, fmt.Errorf("failed to create temp dir: %w", err)
	}
	defer os.RemoveAll(tempDir)

	tempRepo := filepath.Join(tempDir, "repo")
	cloneCmd := exec.Command("git", "clone", cloneURL, tempRepo)
	cloneOutput, err := cloneCmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("failed to clone repo: %w\nOutput: %s", err, string(cloneOutput))
	}

	// Generate branch name with timestamp
	branchName := fmt.Sprintf("workspace-%d", time.Now().Unix())

	// Create and checkout new branch
	gitCheckout := exec.Command("git", "checkout", "-b", branchName)
	gitCheckout.Dir = tempRepo
	if output, err := gitCheckout.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("git checkout failed: %w\nOutput: %s", err, string(output))
	}

	// Copy files respecting .gitignore
	if err := utils.CopyFilesRespectingGitignore(sourceDir, tempRepo); err != nil {
		return nil, fmt.Errorf("failed to copy files: %w", err)
	}

	// Commit and push
	gitAdd := exec.Command("git", "add", ".")
	gitAdd.Dir = tempRepo
	if output, err := gitAdd.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("git add failed: %w\nOutput: %s", err, string(output))
	}

	// Check if there are changes
	gitStatus := exec.Command("git", "status", "--porcelain")
	gitStatus.Dir = tempRepo
	statusOutput, err := gitStatus.Output()
	if err != nil {
		return nil, fmt.Errorf("git status failed: %w", err)
	}

	if len(strings.TrimSpace(string(statusOutput))) == 0 {
		// No changes to push - still return authenticated clone URL
		authenticatedCloneURL := repo.CloneURL
		if strings.HasPrefix(authenticatedCloneURL, "https://") {
			authenticatedCloneURL = strings.Replace(authenticatedCloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
		}
		return &PushResult{
			RepoURL:    repo.CloneURL,
			CloneCmd:   fmt.Sprintf("git clone -b %s %s", branchName, authenticatedCloneURL),
			BranchName: branchName,
		}, nil
	}

	// Commit changes
	gitCommit := exec.Command("git", "commit", "-m", "Sync from local workspace")
	gitCommit.Dir = tempRepo
	if output, err := gitCommit.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("git commit failed: %w\nOutput: %s", err, string(output))
	}

	// Push to remote branch
	gitPush := exec.Command("git", "push", "-u", "origin", branchName)
	gitPush.Dir = tempRepo
	if output, err := gitPush.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("git push failed: %w\nOutput: %s", err, string(output))
	}

	// Build authenticated clone URL for the user
	authenticatedCloneURL := repo.CloneURL
	if strings.HasPrefix(authenticatedCloneURL, "https://") {
		authenticatedCloneURL = strings.Replace(authenticatedCloneURL, "https://", fmt.Sprintf("https://%s:%s@", creds.Username, creds.Password), 1)
	}

	// Return success with authenticated clone command
	cloneCommand := fmt.Sprintf("git clone -b %s %s", branchName, authenticatedCloneURL)
	return &PushResult{
		RepoURL:    repo.CloneURL,
		CloneCmd:   cloneCommand,
		BranchName: branchName,
	}, nil
}

// MergeToMain merges a workspace branch to main and returns the git hash
func (s *GiteaService) MergeToMain(ctx context.Context, serviceName string, branchName string) (string, error) {
	// Get Gitea credentials
	creds, err := s.GetCredentials(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to get credentials: %w", err)
	}

	// Find simulator by service name
	simulators, err := s.ListSimulators(ctx)
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
	repo, err := s.GetSimulatorRepository(ctx, simulator.ID)
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
	cloneOutput, err := cloneCmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("failed to clone repo: %w\nOutput: %s", err, string(cloneOutput))
	}

	// Checkout the workspace branch
	gitCheckout := exec.Command("git", "checkout", branchName)
	gitCheckout.Dir = tempRepo
	if output, err := gitCheckout.CombinedOutput(); err != nil {
		return "", fmt.Errorf("git checkout failed: %w\nOutput: %s", err, string(output))
	}

	// Get the current commit hash
	gitRevParse := exec.Command("git", "rev-parse", "HEAD")
	gitRevParse.Dir = tempRepo
	hashOutput, err := gitRevParse.Output()
	if err != nil {
		return "", fmt.Errorf("git rev-parse failed: %w", err)
	}
	gitHash := strings.TrimSpace(string(hashOutput))

	// Checkout main branch
	gitCheckoutMain := exec.Command("git", "checkout", "main")
	gitCheckoutMain.Dir = tempRepo
	if output, err := gitCheckoutMain.CombinedOutput(); err != nil {
		return "", fmt.Errorf("git checkout main failed: %w\nOutput: %s", err, string(output))
	}

	// Force merge (reset main to workspace branch)
	gitReset := exec.Command("git", "reset", "--hard", branchName)
	gitReset.Dir = tempRepo
	if output, err := gitReset.CombinedOutput(); err != nil {
		return "", fmt.Errorf("git reset failed: %w\nOutput: %s", err, string(output))
	}

	// Force push to main
	gitPush := exec.Command("git", "push", "-f", "origin", "main")
	gitPush.Dir = tempRepo
	if output, err := gitPush.CombinedOutput(); err != nil {
		return "", fmt.Errorf("git push main failed: %w\nOutput: %s", err, string(output))
	}

	return gitHash, nil
}
