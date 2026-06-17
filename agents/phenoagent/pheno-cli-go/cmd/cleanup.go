package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"
)

var (
	cleanupRepo       string
	cleanupDryRun    bool
	cleanupBranches bool
	cleanupGc       bool
)

var cleanupCmd = &cobra.Command{
	Use:   "cleanup",
	Short: "Clean up merged branches, stale worktrees, and optimize repositories",
	Long: `Cleanup performs maintenance operations on repositories:
- Remove merged local branches (except main, master, develop)
- List stale worktrees
- Remove untracked files
- Prune reflog and run garbage collection

Examples:
  # Preview cleanup actions without making changes
  pheno cleanup --dry-run

  # Clean specific repository
  pheno cleanup --repo /path/to/repo

  # Clean only branches (skip other operations)
  pheno cleanup --branches-only`,
	RunE: runCleanup,
}

func init() {
	cleanupCmd.Flags().StringVar(&cleanupRepo, "repo", "", "Specific repository to clean (default: current)")
	cleanupCmd.Flags().BoolVar(&cleanupDryRun, "dry-run", false, "Preview actions without making changes")
	cleanupCmd.Flags().BoolVar(&cleanupBranches, "branches-only", false, "Only clean merged branches")
	cleanupCmd.Flags().BoolVar(&cleanupGc, "gc", true, "Prune reflog and run gc")
}

func runCleanup(cmd *cobra.Command, args []string) error {
	repoPath := cleanupRepo
	if repoPath == "" {
		wd, _ := os.Getwd()
		repoPath = wd
	}

	// Change to repository directory
	if err := os.Chdir(repoPath); err != nil {
		return fmt.Errorf("failed to change to repository: %w", err)
	}

	fmt.Printf("Cleaning repository: %s\n", repoPath)
	fmt.Println(strings.Repeat("=", 50))

	// 1. Remove merged branches
	fmt.Println("\n[1/4] Checking for merged branches...")
	if err := cleanupMergedBranches(); err != nil {
		fmt.Printf("  Warning: %v\n", err)
	}

	// 2. List worktrees
	fmt.Println("\n[2/4] Listing worktrees...")
	if err := listWorktrees(); err != nil {
		fmt.Printf("  Warning: %v\n", err)
	}

	// 3. Garbage collection (if enabled)
	if cleanupGc && !cleanupBranches {
		fmt.Println("\n[3/4] Running garbage collection...")
		if err := runGc(cleanupDryRun); err != nil {
			fmt.Printf("  Warning: %v\n", err)
		}
	}

	fmt.Println("\n✓ Cleanup complete!")

	return nil
}

func cleanupMergedBranches() error {
	// Get current branch
	currentBranch, err := exec.Command("git", "branch", "--show-current").Output()
	if err != nil {
		return fmt.Errorf("failed to get current branch: %w", err)
	}

	// Find merged branches
	merged, err := exec.Command("git", "branch", "--merged", "origin/main").Output()
	if err != nil {
		// Try origin/master if origin/main doesn't exist
		merged, err = exec.Command("git", "branch", "--merged", "origin/master").Output()
		if err != nil {
			return fmt.Errorf("failed to find merged branches: %w", err)
		}
	}

	// Protected branches
	protected := map[string]bool{
		"main":          true,
		"master":        true,
		"develop":       true,
		"staging":       true,
		"production":     true,
		string(currentBranch): true,
	}

	branches := strings.Split(strings.TrimSpace(string(merged)), "\n")
	removed := 0

	for _, branch := range branches {
		branch = strings.TrimSpace(branch)
		if branch == "" {
			continue
		}

		// Skip protected branches
		if protected[branch] {
			continue
		}

		fmt.Printf("  Would remove: %s\n", branch)
		if !cleanupDryRun {
			if err := exec.Command("git", "branch", "-d", branch).Run(); err != nil {
				fmt.Printf("  Warning: failed to remove %s\n", branch)
				continue
			}
		}
		removed++
	}

	if removed == 0 {
		fmt.Println("  No merged branches to remove")
	}

	return nil
}

func listWorktrees() error {
	output, err := exec.Command("git", "worktree", "list").Output()
	if err != nil {
		return fmt.Errorf("failed to list worktrees: %w", err)
	}

	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	fmt.Printf("  Found %d worktrees\n", len(lines))
	for _, line := range lines[1:] { // Skip header
		if strings.TrimSpace(line) != "" {
			fmt.Printf("  %s\n", strings.TrimSpace(line))
		}
	}

	return nil
}

func runGc(dryRun bool) error {
	if dryRun {
		fmt.Println("  Would run: git reflog expire && git gc --prune=now")
		return nil
	}

	// Expire reflog
	if err := exec.Command("git", "reflog", "expire", "--expire=now", "--all").Run(); err != nil {
		return fmt.Errorf("failed to expire reflog: %w", err)
	}

	// Garbage collect
	if err := exec.Command("git", "gc", "--prune=now", "--aggressive").Run(); err != nil {
		return fmt.Errorf("failed to run gc: %w", err)
	}

	fmt.Println("  Garbage collection complete")
	return nil
}
