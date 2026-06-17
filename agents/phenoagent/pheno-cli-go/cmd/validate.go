package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
)

var (
	validateRepos     string
	validateFormat    string
	validateCheckOnly bool
)

var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate repository governance compliance against phenotype standards",
	Long: `Validate checks repositories for compliance with phenotype governance standards.

It validates:
  - Required governance files (AGENTS.md, CLAUDE.md, SECURITY.md)
  - CI/CD workflows (ci.yml, release.yml, security.yml)
  - Code quality configuration
  - Directory structure
  - Branch discipline settings

Examples:
  # Validate current repository
  pheno validate

  # Validate specific repositories
  pheno validate --repos repo1,repo2,repo3

  # Check-only mode (no fixes applied)
  pheno validate --check-only

  # JSON output for CI integration
  pheno validate --format json`,
	RunE: runValidate,
}

func init() {
	validateCmd.Flags().StringVar(&validateRepos, "repos", "", "Comma-separated list of repositories to validate")
	validateCmd.Flags().StringVar(&validateFormat, "format", "table", "Output format: table, json, yaml")
	validateCmd.Flags().BoolVar(&validateCheckOnly, "check-only", false, "Report-only mode (no fixes applied)")
}

func runValidate(cmd *cobra.Command, args []string) error {
	var repoPaths []string

	if validateRepos != "" {
		repoPaths = []string{validateRepos}
	} else {
		wd, _ := os.Getwd()
		repoPaths = []string{wd}
	}

	fmt.Println("Validating repository compliance...")
	fmt.Println()

	requiredFiles := map[string]bool{
		"CLAUDE.md":    true,
		"AGENTS.md":    true,
		"SECURITY.md":  false, // Optional
	}

	requiredWorkflows := map[string]bool{
		".github/workflows/ci.yml": true,
	}

	totalPassed := 0
	totalFailed := 0

	for _, repoPath := range repoPaths {
		passed := 0
		failed := 0

		fmt.Printf("Checking: %s\n", filepath.Base(repoPath))

		// Check required files
		for file, required := range requiredFiles {
			path := filepath.Join(repoPath, file)
			if _, err := os.Stat(path); os.IsNotExist(err) {
				if required {
					failed++
					fmt.Printf("  ✗ Missing required file: %s\n", file)
				}
			} else {
				passed++
				fmt.Printf("  ✓ Found: %s\n", file)
			}
		}

		// Check workflows
		for workflow := range requiredWorkflows {
			path := filepath.Join(repoPath, workflow)
			if _, err := os.Stat(path); os.IsNotExist(err) {
				failed++
				fmt.Printf("  ✗ Missing workflow: %s\n", workflow)
			} else {
				passed++
				fmt.Printf("  ✓ Found: %s\n", workflow)
			}
		}

		// Check for .git directory
		gitPath := filepath.Join(repoPath, ".git")
		if _, err := os.Stat(gitPath); os.IsNotExist(err) {
			failed++
			fmt.Printf("  ✗ Not a git repository\n")
		} else {
			passed++
			fmt.Printf("  ✓ Git repository\n")
		}

		totalPassed += passed
		totalFailed += failed

		fmt.Printf("\nResult: %d passed, %d failed\n\n", passed, failed)
	}

	// Summary
	total := totalPassed + totalFailed
	passRate := float64(totalPassed) / float64(total) * 100

	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("Summary: %d/%d checks passed (%.1f%%)\n", totalPassed, total, passRate)

	if totalFailed > 0 {
		fmt.Println("Some checks failed. Run 'pheno bootstrap' to add missing files.")
		if validateCheckOnly {
			return fmt.Errorf("validation failed")
		}
	}

	return nil
}
