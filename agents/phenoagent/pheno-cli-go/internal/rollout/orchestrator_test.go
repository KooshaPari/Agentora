package rollout

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// setupGoRepo creates a minimal Go repo structure in dir/name.
func setupGoRepo(t *testing.T, base, name string) string {
	t.Helper()
	repoPath := filepath.Join(base, name)
	if err := os.MkdirAll(repoPath, 0755); err != nil {
		t.Fatalf("mkdir %s: %v", repoPath, err)
	}
	if err := os.WriteFile(filepath.Join(repoPath, "go.mod"), []byte("module example.com/"+name+"\ngo 1.21\n"), 0644); err != nil {
		t.Fatalf("write go.mod: %v", err)
	}
	// Initialize a fake .git directory so hooks can be written
	if err := os.MkdirAll(filepath.Join(repoPath, ".git", "hooks"), 0755); err != nil {
		t.Fatalf("mkdir .git/hooks: %v", err)
	}
	return repoPath
}

func TestRunBulkBootstrap_AutoDetect(t *testing.T) {
	dir := t.TempDir()
	setupGoRepo(t, dir, "service-a")
	setupGoRepo(t, dir, "service-b")

	// Non-code dir should be ignored
	if err := os.MkdirAll(filepath.Join(dir, "docs"), 0755); err != nil {
		t.Fatal(err)
	}

	opts := RolloutOptions{
		ReposDir: dir,
		DryRun:   true,
	}

	results, err := RunBulkBootstrap(context.Background(), opts)
	if err != nil {
		t.Fatalf("RunBulkBootstrap error: %v", err)
	}

	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d: %+v", len(results), results)
	}

	for _, r := range results {
		if !r.Success {
			t.Errorf("repo %s failed: %s", r.Repo, r.Error)
		}
		if len(r.FilesCreated) == 0 {
			t.Errorf("repo %s: expected files in dry-run, got none", r.Repo)
		}
	}
}

func TestRunBulkBootstrap_WithManifest(t *testing.T) {
	dir := t.TempDir()
	setupGoRepo(t, dir, "api")

	tomlContent := `
[[repos]]
name = "api"
language = "go"
registry = "go_proxy"
risk_profile = "low"
`
	manifestPath := filepath.Join(dir, "repos.toml")
	if err := os.WriteFile(manifestPath, []byte(tomlContent), 0644); err != nil {
		t.Fatal(err)
	}

	opts := RolloutOptions{
		ReposDir:     dir,
		ManifestPath: manifestPath,
		DryRun:       true,
	}

	results, err := RunBulkBootstrap(context.Background(), opts)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if !results[0].Success {
		t.Errorf("expected success, got error: %s", results[0].Error)
	}
}

func TestRunBulkBootstrap_Skip(t *testing.T) {
	dir := t.TempDir()
	setupGoRepo(t, dir, "skip-me")
	setupGoRepo(t, dir, "keep-me")

	opts := RolloutOptions{
		ReposDir: dir,
		DryRun:   true,
		Skip:     []string{"skip-me"},
	}

	results, err := RunBulkBootstrap(context.Background(), opts)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	skipped := 0
	processed := 0
	for _, r := range results {
		if r.Error == "skipped" {
			skipped++
		} else {
			processed++
		}
	}

	if skipped != 1 {
		t.Errorf("expected 1 skipped, got %d", skipped)
	}
	if processed != 1 {
		t.Errorf("expected 1 processed, got %d", processed)
	}
}

func TestRunBulkBootstrap_SkipFlag(t *testing.T) {
	dir := t.TempDir()

	tomlContent := `
[[repos]]
name = "skip-by-flag"
language = "go"
skip = true

[[repos]]
name = "normal"
language = "go"
`
	manifestPath := filepath.Join(dir, "repos.toml")
	if err := os.WriteFile(manifestPath, []byte(tomlContent), 0644); err != nil {
		t.Fatal(err)
	}
	setupGoRepo(t, dir, "normal")

	opts := RolloutOptions{
		ReposDir:     dir,
		ManifestPath: manifestPath,
		DryRun:       true,
	}

	results, err := RunBulkBootstrap(context.Background(), opts)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}

	skippedCount := 0
	for _, r := range results {
		if r.Error == "skipped" {
			skippedCount++
		}
	}
	if skippedCount != 1 {
		t.Errorf("expected 1 skipped result, got %d", skippedCount)
	}
}

func TestRunBulkBootstrap_ContextCancellation(t *testing.T) {
	dir := t.TempDir()
	setupGoRepo(t, dir, "repo-a")
	setupGoRepo(t, dir, "repo-b")

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // cancel immediately

	opts := RolloutOptions{
		ReposDir: dir,
		DryRun:   true,
	}

	// Should not panic and should return (possibly empty) results
	_, err := RunBulkBootstrap(ctx, opts)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestFormatResults(t *testing.T) {
	results := []RolloutResult{
		{Repo: "service-a", Success: true, FilesCreated: []string{"mise.toml", "cliff.toml"}},
		{Repo: "service-b", Success: false, Error: "template error"},
		{Repo: "service-c", Success: true, Error: "skipped"},
	}

	output := FormatResults(results)

	if !strings.Contains(output, "service-a") {
		t.Error("expected service-a in output")
	}
	if !strings.Contains(output, "FAIL") {
		t.Error("expected FAIL in output")
	}
	if !strings.Contains(output, "SKIP") {
		t.Error("expected SKIP in output")
	}
	if !strings.Contains(output, "1 OK") {
		t.Error("expected '1 OK' in summary")
	}
	if !strings.Contains(output, "1 failed") {
		t.Error("expected '1 failed' in summary")
	}
	if !strings.Contains(output, "1 skipped") {
		t.Error("expected '1 skipped' in summary")
	}
}

func TestFormatResults_Empty(t *testing.T) {
	output := FormatResults(nil)
	if !strings.Contains(output, "No repositories") {
		t.Error("expected empty message")
	}
}
