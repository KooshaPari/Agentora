package pilot

import (
	"fmt"
	"os"
	"path/filepath"
)

// Check represents a single validation check result.
type Check struct {
	Name   string
	Passed bool
	Detail string
}

// PilotReport holds the results of a pilot repo validation.
type PilotReport struct {
	RepoPath string
	Checks   []Check
	Passed   bool
}

// ValidatePilotRepo checks that a repository has been bootstrapped correctly
// for pilot rollout: mise.toml exists, hooks are installed, and CI workflows
// are present.
func ValidatePilotRepo(repoPath string) (*PilotReport, error) {
	if _, err := os.Stat(repoPath); err != nil {
		return nil, fmt.Errorf("repo path does not exist: %w", err)
	}

	report := &PilotReport{RepoPath: repoPath}

	report.Checks = append(report.Checks, checkMiseToml(repoPath))
	report.Checks = append(report.Checks, checkCIWorkflows(repoPath))
	report.Checks = append(report.Checks, checkGitHooks(repoPath))

	allPassed := true
	for _, c := range report.Checks {
		if !c.Passed {
			allPassed = false
			break
		}
	}
	report.Passed = allPassed

	return report, nil
}

func checkMiseToml(repoPath string) Check {
	p := filepath.Join(repoPath, "mise.toml")
	if _, err := os.Stat(p); err != nil {
		return Check{Name: "mise.toml exists", Passed: false, Detail: "mise.toml not found"}
	}
	return Check{Name: "mise.toml exists", Passed: true, Detail: p}
}

func checkCIWorkflows(repoPath string) Check {
	dir := filepath.Join(repoPath, ".github", "workflows")
	entries, err := os.ReadDir(dir)
	if err != nil {
		return Check{Name: "CI workflows installed", Passed: false, Detail: ".github/workflows not found or unreadable"}
	}
	for _, e := range entries {
		if !e.IsDir() {
			return Check{Name: "CI workflows installed", Passed: true, Detail: fmt.Sprintf("%d workflow(s) found", countFiles(entries))}
		}
	}
	return Check{Name: "CI workflows installed", Passed: false, Detail: "no workflow files in .github/workflows"}
}

func checkGitHooks(repoPath string) Check {
	hooksDir := filepath.Join(repoPath, ".git", "hooks")
	entries, err := os.ReadDir(hooksDir)
	if err != nil {
		return Check{Name: "Git hooks installed", Passed: false, Detail: ".git/hooks not found or unreadable"}
	}
	for _, e := range entries {
		if !e.IsDir() {
			return Check{Name: "Git hooks installed", Passed: true, Detail: fmt.Sprintf("%d hook(s) found", countFiles(entries))}
		}
	}
	return Check{Name: "Git hooks installed", Passed: false, Detail: "no hooks found in .git/hooks"}
}

func countFiles(entries []os.DirEntry) int {
	count := 0
	for _, e := range entries {
		if !e.IsDir() {
			count++
		}
	}
	return count
}
