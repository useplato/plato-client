// Package models provides data structures for simulator-related operations.
//
// This file defines models for Plato simulators and their versions. These models
// are used when listing available simulators and querying version information
// including artifact IDs, datasets, and creation timestamps.
package models

type SimulatorListItem struct {
	ID              int     `json:"id"`
	Name            string  `json:"name"`
	Description     *string `json:"description"`
	ImgURL          *string `json:"img_url"`
	Enabled         bool    `json:"enabled"`
	SimType         string  `json:"sim_type"`
	JobName         *string `json:"job_name"`
	InternalAppPort *int    `json:"internal_app_port"`
	VersionTag      string  `json:"version_tag"`
	ImageURI        *string `json:"image_uri"`
}

type SimulatorVersion struct {
	ArtifactID string `json:"artifact_id"`
	Version    string `json:"version"`
	Dataset    string `json:"dataset"`
	CreatedAt  string `json:"created_at"`
}
