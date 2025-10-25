// Package models provides data structures for Gitea integration.
//
// This file defines models for Gitea authentication, simulators with repository
// information, and repository metadata. Gitea is used as the git hosting platform
// for simulator source code, allowing users to clone, modify, and version control
// their simulators.
package models

// GiteaCredentials represents Gitea authentication credentials
type GiteaCredentials struct {
	Username string `json:"username"`
	Password string `json:"password"`
	OrgName  string `json:"org_name"`
}

// GiteaSimulator represents a simulator with Gitea repository info
type GiteaSimulator struct {
	ID             int    `json:"id"`
	Name           string `json:"name"`
	HasRepo        bool   `json:"has_repo"`
	GiteaRepoOwner string `json:"gitea_repo_owner"`
	GiteaRepoName  string `json:"gitea_repo_name"`
}

// GiteaRepository represents a Gitea repository
type GiteaRepository struct {
	Name        string `json:"name"`
	FullName    string `json:"full_name"`
	CloneURL    string `json:"clone_url"`
	SSHURL      string `json:"ssh_url"`
	Description string `json:"description"`
	Private     bool   `json:"private"`
	HasRepo     bool   `json:"has_repo"`
}
