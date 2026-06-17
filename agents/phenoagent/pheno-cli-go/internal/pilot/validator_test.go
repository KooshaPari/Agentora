package pilot

import (
	"os"
	"path/filepath"
	"testing"
)

func TestValidatePilotRepo_NonExistent(t *testing.T) {
	_, err := ValidatePilotRepo("/nonexistent/path/xyz")
	if err == nil {
		t.Fatal("expected error for non-existent path, got nil")
	}
}

func TestValidatePilotRepo_AllChecksPass(t *testing.T) {
	dir := t.TempDir()

	// Create mise.toml
	if err := os.WriteFile(filepath.Join(dir, "mise.toml"), []byte("[tools]\nnode = \"20.x\"\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Create .github/workflows with a workflow file
	wfDir := filepath.Join(dir, ".github", "workflows")
	if err := os.MkdirAll(wfDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(wfDir, "ci.yml"), []byte("name: CI\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Create .git/hooks with a hook file
	hooksDir := filepath.Join(dir, ".git", "hooks")
	if err := os.MkdirAll(hooksDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(hooksDir, "pre-commit"), []byte("#!/bin/sh\n"), 0o755); err != nil {
		t.Fatal(err)
	}

	report, err := ValidatePilotRepo(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !report.Passed {
		for _, c := range report.Checks {
			if !c.Passed {
				t.Errorf("check %q failed: %s", c.Name, c.Detail)
			}
		}
	}
}

func TestValidatePilotRepo_MissingMiseToml(t *testing.T) {
	dir := t.TempDir()

	// Create workflows and hooks but no mise.toml
	wfDir := filepath.Join(dir, ".github", "workflows")
	if err := os.MkdirAll(wfDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(wfDir, "ci.yml"), []byte("name: CI\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	hooksDir := filepath.Join(dir, ".git", "hooks")
	if err := os.MkdirAll(hooksDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(hooksDir, "pre-commit"), []byte("#!/bin/sh\n"), 0o755); err != nil {
		t.Fatal(err)
	}

	report, err := ValidatePilotRepo(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if report.Passed {
		t.Fatal("expected report to fail when mise.toml is missing")
	}

	var misePassed bool
	for _, c := range report.Checks {
		if c.Name == "mise.toml exists" {
			misePassed = c.Passed
		}
	}
	if misePassed {
		t.Error("expected mise.toml check to fail")
	}
}

func TestValidatePilotRepo_MissingWorkflows(t *testing.T) {
	dir := t.TempDir()

	if err := os.WriteFile(filepath.Join(dir, "mise.toml"), []byte("[tools]\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	hooksDir := filepath.Join(dir, ".git", "hooks")
	if err := os.MkdirAll(hooksDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(hooksDir, "pre-commit"), []byte("#!/bin/sh\n"), 0o755); err != nil {
		t.Fatal(err)
	}

	report, err := ValidatePilotRepo(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if report.Passed {
		t.Fatal("expected report to fail when workflows are missing")
	}
}

func TestValidatePilotRepo_CheckCount(t *testing.T) {
	dir := t.TempDir()

	report, err := ValidatePilotRepo(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(report.Checks) != 3 {
		t.Errorf("expected 3 checks, got %d", len(report.Checks))
	}
}
