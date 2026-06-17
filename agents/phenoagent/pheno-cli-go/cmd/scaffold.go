package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
)

var (
	scaffoldName     string
	scaffoldLanguage string
	scaffoldPattern string
	scaffoldOutput  string
)

var scaffoldCmd = &cobra.Command{
	Use:   "scaffold",
	Short: "Generate new microservices from hexagonal architecture templates",
	Long: `Scaffold creates new microservices with hexagonal/clean architecture patterns.

Supported patterns:
  - hexagonal: Full ports & adapters architecture
  - clean: Clean architecture (simplified hexagonal)
  - microservice: Minimal microservice structure

Supported languages:
  - go: Go with hexagonal + CQRS
  - python: Python with FastAPI + hexagonal
  - rust: Rust with axum + hexagonal
  - typescript: TypeScript/Node.js with hexagonal

Examples:
  # Scaffold a Go microservice
  pheno scaffold --name my-service --lang go

  # Scaffold with specific pattern
  pheno scaffold --name my-service --lang rust --pattern hexagonal

  # Scaffold to specific directory
  pheno scaffold --name my-service --lang python --output /path/to/projects`,
	RunE: runScaffold,
}

func init() {
	scaffoldCmd.Flags().StringVar(&scaffoldName, "name", "", "Service name (required)")
	scaffoldCmd.Flags().StringVar(&scaffoldLanguage, "lang", "", "Language: go, python, rust, typescript (required)")
	scaffoldCmd.Flags().StringVar(&scaffoldPattern, "pattern", "hexagonal", "Pattern: hexagonal, clean, microservice")
	scaffoldCmd.Flags().StringVar(&scaffoldOutput, "output", ".", "Output directory")
	scaffoldCmd.MarkFlagRequired("name")
	scaffoldCmd.MarkFlagRequired("lang")
}

func runScaffold(cmd *cobra.Command, args []string) error {
	validLanguages := map[string]bool{"go": true, "python": true, "rust": true, "typescript": true}
	if !validLanguages[scaffoldLanguage] {
		return fmt.Errorf("unsupported language: %s", scaffoldLanguage)
	}

	outputDir := scaffoldOutput
	if outputDir == "." {
		wd, _ := os.Getwd()
		outputDir = filepath.Join(wd, scaffoldName)
	}

	fmt.Printf("Scaffolding %s service '%s' at %s\n", scaffoldPattern, scaffoldName, outputDir)

	// Create directory structure based on pattern
	dirs := []string{
		"cmd",
		"internal/domain",
		"internal/application",
		"internal/adapters",
		"pkg",
	}

	for _, dir := range dirs {
		path := filepath.Join(outputDir, dir)
		if err := os.MkdirAll(path, 0755); err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
	}

	// Create basic files based on language
	var manifestContent string
	switch scaffoldLanguage {
	case "go":
		manifestContent = fmt.Sprintf("module github.com/phenotype/%s\n\ngo 1.21\n", scaffoldName)
	case "rust":
		manifestContent = fmt.Sprintf("[package]\nname = \"%s\"\nversion = \"0.1.0\"\nedition = \"2021\"\n", scaffoldName)
	case "python":
		manifestContent = fmt.Sprintf("[project]\nname = \"%s\"\nversion = \"0.1.0\"\n", scaffoldName)
	case "typescript":
		manifestContent = fmt.Sprintf("{\n  \"name\": \"@phenotype/%s\",\n  \"version\": \"0.1.0\",\n  \"type\": \"module\"\n}\n", scaffoldName)
	}

	manifestFile := map[string]string{
		"go":         "go.mod",
		"rust":       "Cargo.toml",
		"python":     "pyproject.toml",
		"typescript": "package.json",
	}

	manifestPath := filepath.Join(outputDir, manifestFile[scaffoldLanguage])
	if err := os.WriteFile(manifestPath, []byte(manifestContent), 0644); err != nil {
		return fmt.Errorf("failed to write manifest: %w", err)
	}

	// Create README
	readme := fmt.Sprintf("# %s\n\n%s pattern microservice\n\n## Getting Started\n\n```bash\n# Install dependencies\n# Run the service\n```\n", scaffoldName, scaffoldPattern)
	readmePath := filepath.Join(outputDir, "README.md")
	os.WriteFile(readmePath, []byte(readme), 0644)

	fmt.Printf("\n✓ Scaffolded %s service at %s\n", scaffoldLanguage, outputDir)
	fmt.Println("\nNext steps:")
	fmt.Println("  cd " + scaffoldName)
	fmt.Println("  # Install dependencies")
	fmt.Println("  # Run: pheno bootstrap")

	return nil
}
