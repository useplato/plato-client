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
