package cmd

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/spf13/cobra"
)

func TestPublishDryRun(t *testing.T) {
	// Create a temporary directory
	tmpDir, err := os.MkdirTemp("", "pheno-test-*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create a minimal package.json
	packageJSON := `{
		"name": "test-package",
		"version": "1.0.0",
		"private": false
	}`
	pkgPath := filepath.Join(tmpDir, "package.json")
	if err := os.WriteFile(pkgPath, []byte(packageJSON), 0644); err != nil {
		t.Fatalf("failed to write package.json: %v", err)
	}

	// Change to the temporary directory
	oldWd, err := os.Getwd()
	if err != nil {
		t.Fatalf("failed to get current directory: %v", err)
	}
	if err := os.Chdir(tmpDir); err != nil {
		t.Fatalf("failed to change directory: %v", err)
	}
	defer os.Chdir(oldWd)

	// Create the publish command with dry-run flag
	cmd := &cobra.Command{
		Use:   "publish",
		Short: "Publish packages to their registries",
		RunE:  runPublish,
	}
	cmd.Flags().String("registry", "", "registry to publish to")
	cmd.Flags().String("version", "", "version to publish")
	cmd.Flags().String("channel", "alpha", "release channel")
	cmd.Flags().Bool("dry-run", true, "dry-run mode")

	// Execute the command
	err = cmd.RunE(cmd, []string{})
	if err != nil {
		t.Fatalf("publish command failed: %v", err)
	}
}
