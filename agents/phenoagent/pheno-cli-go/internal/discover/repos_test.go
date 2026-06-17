package discover

import (
	"os"
	"path/filepath"
	"testing"
)

func TestFindRepositories(t *testing.T) {
	// Create a temporary directory structure
	tmpDir := t.TempDir()

	// Create test directory structure:
	// tmpDir/
	//   repo1/.git/
	//   repo1/go.mod
	//   repo2/
	//     package.json
	//   skip_me/node_modules/
	//   skip_me/.git/

	repo1 := filepath.Join(tmpDir, "repo1")
	if err := os.Mkdir(repo1, 0755); err != nil {
		t.Fatalf("failed to create repo1: %v", err)
	}

	gitDir := filepath.Join(repo1, ".git")
	if err := os.Mkdir(gitDir, 0755); err != nil {
		t.Fatalf("failed to create .git: %v", err)
	}

	if err := os.WriteFile(filepath.Join(repo1, "go.mod"), []byte("module test"), 0644); err != nil {
		t.Fatalf("failed to create go.mod: %v", err)
	}

	repo2 := filepath.Join(tmpDir, "repo2")
	if err := os.Mkdir(repo2, 0755); err != nil {
		t.Fatalf("failed to create repo2: %v", err)
	}

	if err := os.WriteFile(filepath.Join(repo2, "package.json"), []byte("{}"), 0644); err != nil {
		t.Fatalf("failed to create package.json: %v", err)
	}

	skipDir := filepath.Join(tmpDir, "skip_me")
	if err := os.Mkdir(skipDir, 0755); err != nil {
		t.Fatalf("failed to create skip_me: %v", err)
	}

	nodeModules := filepath.Join(skipDir, "node_modules")
	if err := os.Mkdir(nodeModules, 0755); err != nil {
		t.Fatalf("failed to create node_modules: %v", err)
	}

	// Test discovery
	repos, err := FindRepositories(tmpDir)
	if err != nil {
		t.Fatalf("FindRepositories failed: %v", err)
	}

	// Verify results
	if len(repos) < 2 {
		t.Errorf("expected at least 2 repositories, got %d", len(repos))
	}

	foundRepo1 := false
	foundRepo2 := false

	for _, repo := range repos {
		if repo.Name == "repo1" {
			foundRepo1 = true
			if !repo.HasGit {
				t.Errorf("repo1 should have git")
			}
		}
		if repo.Name == "repo2" {
			foundRepo2 = true
			if repo.HasGit {
				t.Errorf("repo2 should not have git")
			}
		}
	}

	if !foundRepo1 {
		t.Error("repo1 not found")
	}
	if !foundRepo2 {
		t.Error("repo2 not found")
	}
}
