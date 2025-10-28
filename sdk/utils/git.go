package utils

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// CopyFilesRespectingGitignore copies files from src to dst while respecting .gitignore rules
func CopyFilesRespectingGitignore(src, dst string) error {
	// First copy .gitignore if it exists
	gitignoreSrc := filepath.Join(src, ".gitignore")
	if _, err := os.Stat(gitignoreSrc); err == nil {
		gitignoreDst := filepath.Join(dst, ".gitignore")
		if _, err := os.Stat(gitignoreDst); os.IsNotExist(err) {
			input, err := os.ReadFile(gitignoreSrc)
			if err != nil {
				return err
			}
			if err := os.WriteFile(gitignoreDst, input, 0644); err != nil {
				return err
			}
		}
	}

	// Helper to check if path should be copied
	shouldCopy := func(path string) bool {
		baseName := filepath.Base(path)
		// Skip .git directories and .plato-hub.json
		if strings.HasPrefix(baseName, ".git") || baseName == ".plato-hub.json" {
			return false
		}

		// Use git check-ignore to respect .gitignore rules
		cmd := exec.Command("git", "check-ignore", "-q", path)
		cmd.Dir = src
		err := cmd.Run()
		// git check-ignore returns 0 if path IS ignored, 1 if NOT ignored
		return err != nil // Return true if NOT ignored
	}

	// Walk through source directory
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Get relative path
		relPath, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}

		// Skip root directory
		if relPath == "." {
			return nil
		}

		// Check if should copy
		if !shouldCopy(path) {
			if info.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}

		dstPath := filepath.Join(dst, relPath)

		if info.IsDir() {
			return os.MkdirAll(dstPath, info.Mode())
		}

		// Copy file
		input, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(dstPath, input, info.Mode())
	})
}
