package cmd

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/KooshaPari/pheno-cli/internal/detect"
	"github.com/KooshaPari/pheno-cli/internal/rollout"
	"github.com/KooshaPari/pheno-cli/internal/templates"
	"github.com/spf13/cobra"
)

var (
	bootstrapLanguage    string
	bootstrapRiskProfile string
	bootstrapDryRun      bool
	bootstrapForce       bool
	bootstrapAll         bool
	bootstrapReposDir    string
	bootstrapSkip        []string
	bootstrapManifest    string
)

var bootstrapCmd = &cobra.Command{
	Use:   "bootstrap",
	Short: "Bootstrap governance artifacts for a repository",
	Long: `Bootstrap creates essential governance and DX artifacts for a repository:
- mise.toml: Task automation config
- .git/hooks/pre-commit: Commit message validation
- .git/hooks/pre-push: Pre-push checks
- .github/workflows/ci.yml: CI workflow
- .github/workflows/release.yml: Release workflow
- cliff.toml: Changelog generation config

Use --all to bootstrap all repositories in a directory.`,
	RunE: runBootstrap,
}

func init() {
	bootstrapCmd.Flags().StringVar(&bootstrapLanguage, "language", "", "Programming language (go, rust, python, typescript). If not specified, detected from manifests.")
	bootstrapCmd.Flags().StringVar(&bootstrapRiskProfile, "risk-profile", "low", "Risk profile (low, medium, high)")
	bootstrapCmd.Flags().BoolVar(&bootstrapDryRun, "dry-run", false, "Show files that would be created without writing them")
	bootstrapCmd.Flags().BoolVar(&bootstrapForce, "force", false, "Overwrite existing files")
	bootstrapCmd.Flags().BoolVar(&bootstrapAll, "all", false, "Bootstrap all repositories in --repos-dir")
	bootstrapCmd.Flags().StringVar(&bootstrapReposDir, "repos-dir", "", "Directory containing repositories (used with --all)")
	bootstrapCmd.Flags().StringSliceVar(&bootstrapSkip, "skip", nil, "Comma-separated list of repo names to skip (used with --all)")
	bootstrapCmd.Flags().StringVar(&bootstrapManifest, "manifest", "", "Path to repos.toml manifest (used with --all; auto-detects if omitted)")
}

func runBootstrap(cmd *cobra.Command, args []string) error {
	if bootstrapAll {
		return runBulkBootstrap(cmd)
	}
	return runSingleBootstrap(cmd, args)
}

func runBulkBootstrap(cmd *cobra.Command) error {
	reposDir := bootstrapReposDir
	if reposDir == "" {
		var err error
		reposDir, err = os.Getwd()
		if err != nil {
			return fmt.Errorf("failed to get current directory: %w", err)
		}
	}

	opts := rollout.RolloutOptions{
		ReposDir:     reposDir,
		ManifestPath: bootstrapManifest,
		DryRun:       bootstrapDryRun,
		Skip:         bootstrapSkip,
	}

	results, err := rollout.RunBulkBootstrap(context.Background(), opts)
	if err != nil {
		return err
	}

	fmt.Print(rollout.FormatResults(results))
	return nil
}

func runSingleBootstrap(cmd *cobra.Command, args []string) error {
	// Get the current working directory (repository root)
	repoPath, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("failed to get current directory: %w", err)
	}

	// Detect language if not specified
	language := bootstrapLanguage
	if language == "" {
		detected := detect.DetectLanguages(repoPath)
		if len(detected) == 0 {
			return fmt.Errorf("could not detect programming language. Please specify with --language flag")
		}
		// Use the first detected language
		language = string(detected[0].Language)
		fmt.Printf("→ Detected language: %s\n", language)
	} else {
		// Validate the specified language
		validLanguages := map[string]bool{"go": true, "rust": true, "python": true, "typescript": true}
		if !validLanguages[language] {
			return fmt.Errorf("unsupported language: %s. Supported: go, rust, python, typescript", language)
		}
	}

	// Determine repository name from the directory
	repoName := filepath.Base(repoPath)

	// Build the template context
	ctx := templates.TemplateContext{
		RepoName:    repoName,
		Language:    language,
		Registry:    inferRegistry(language),
		RiskProfile: bootstrapRiskProfile,
	}

	// Define files to generate
	filesToGenerate := map[string]string{
		"mise.toml":                     "mise.toml",
		".git/hooks/pre-commit":         "pre-commit.sh",
		".git/hooks/pre-push":           "pre-push.sh",
		".github/workflows/ci.yml":      "ci.yml",
		".github/workflows/release.yml": "release.yml",
	}

	// Render all templates
	renderedFiles := make(map[string]string)
	for filePath, templateName := range filesToGenerate {
		content, err := templates.RenderTemplate(templateName, ctx)
		if err != nil {
			return fmt.Errorf("failed to render template %s: %w", templateName, err)
		}
		renderedFiles[filePath] = content
	}

	// Add static cliff.toml
	renderedFiles["cliff.toml"] = templates.GetStaticCliffToml()

	// If dry-run, just print the list of files
	if bootstrapDryRun {
		fmt.Println("✓ Dry-run mode: would create the following files:")
		for filePath := range filesToGenerate {
			fmt.Printf("  - %s\n", filePath)
		}
		return nil
	}

	// Check for existing files if not forcing
	if !bootstrapForce {
		for filePath := range filesToGenerate {
			fullPath := filepath.Join(repoPath, filePath)
			if _, err := os.Stat(fullPath); err == nil {
				return fmt.Errorf("file already exists: %s. Use --force to overwrite", filePath)
			}
		}
	}

	// Write files to disk
	for filePath, content := range renderedFiles {
		fullPath := filepath.Join(repoPath, filePath)

		// Create parent directories if needed
		dir := filepath.Dir(fullPath)
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir, err)
		}

		// Write the file
		if err := os.WriteFile(fullPath, []byte(content), 0644); err != nil {
			return fmt.Errorf("failed to write file %s: %w", filePath, err)
		}

		// Make hook scripts executable
		if strings.HasPrefix(filePath, ".git/hooks/") {
			if err := os.Chmod(fullPath, 0755); err != nil {
				return fmt.Errorf("failed to chmod +x %s: %w", filePath, err)
			}
		}

		fmt.Printf("✓ Created %s\n", filePath)
	}

	fmt.Println("\n✓ Bootstrap complete!")
	fmt.Printf("Repository: %s (%s)\n", repoName, language)
	fmt.Printf("Risk profile: %s\n", bootstrapRiskProfile)
	fmt.Println("\nNext steps:")
	fmt.Println("1. Review the generated files")
	fmt.Println("2. Customize them as needed")
	fmt.Println("3. Commit with: git add . && git commit -m 'chore: bootstrap governance artifacts'")

	return nil
}

// inferRegistry returns the likely registry for a given language
func inferRegistry(language string) string {
	switch language {
	case "go":
		return "go_proxy"
	case "rust":
		return "crates.io"
	case "python":
		return "pypi"
	case "typescript":
		return "npm"
	default:
		return "unknown"
	}
}
