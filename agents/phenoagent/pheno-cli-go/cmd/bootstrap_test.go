package cmd

import (
	"os"
	"path/filepath"
	"testing"
)

func TestBootstrapDryRun(t *testing.T) {
	// Create a temporary directory for the test repository
	tempDir, err := os.MkdirTemp("", "bootstrap-test-")
	if err != nil {
		t.Fatalf("failed to create temp directory: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Save the current working directory
	originalWd, err := os.Getwd()
	if err != nil {
		t.Fatalf("failed to get current directory: %v", err)
	}
	defer os.Chdir(originalWd)

	// Change to the temporary directory
	if err := os.Chdir(tempDir); err != nil {
		t.Fatalf("failed to change directory: %v", err)
	}

	// Create a go.mod file to trigger language detection
	if err := os.WriteFile("go.mod", []byte("module test/repo\n"), 0644); err != nil {
		t.Fatalf("failed to create go.mod: %v", err)
	}

	// Create a test command with dry-run flag
	rootCmd.SetArgs([]string{"bootstrap", "--dry-run"})

	// Execute the command
	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("bootstrap command failed: %v", err)
	}

	// Verify that no files were actually created
	expectedFiles := []string{
		"mise.toml",
		".git/hooks/pre-commit",
		".git/hooks/pre-push",
		".github/workflows/ci.yml",
		".github/workflows/release.yml",
		"cliff.toml",
	}

	for _, file := range expectedFiles {
		fullPath := filepath.Join(tempDir, file)
		if _, err := os.Stat(fullPath); err == nil {
			t.Errorf("expected file %s to not exist in dry-run mode", file)
		}
	}
}

func TestBootstrapWithLanguage(t *testing.T) {
	// Create a temporary directory for the test repository
	tempDir, err := os.MkdirTemp("", "bootstrap-test-")
	if err != nil {
		t.Fatalf("failed to create temp directory: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Save the current working directory
	originalWd, err := os.Getwd()
	if err != nil {
		t.Fatalf("failed to get current directory: %v", err)
	}
	defer os.Chdir(originalWd)

	// Change to the temporary directory
	if err := os.Chdir(tempDir); err != nil {
		t.Fatalf("failed to change directory: %v", err)
	}

	// Create a test command with explicit language flag
	rootCmd.SetArgs([]string{"bootstrap", "--language", "rust", "--dry-run"})

	// Execute the command
	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("bootstrap command failed: %v", err)
	}
}
