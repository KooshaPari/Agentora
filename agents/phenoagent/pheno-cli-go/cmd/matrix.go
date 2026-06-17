package cmd

import (
	"fmt"
	"os"

	"github.com/KooshaPari/pheno-cli/internal/detect"
	"github.com/KooshaPari/pheno-cli/internal/discover"
	"github.com/KooshaPari/pheno-cli/internal/matrix"
	"github.com/spf13/cobra"
)

var matrixCmd = &cobra.Command{
	Use:   "matrix",
	Short: "Generate release matrix",
	RunE:  runMatrix,
}

var (
	matrixOutput string
)

func init() {
	matrixCmd.Flags().StringVar(&matrixOutput, "output", "", "Output file path (prints to stdout if not specified)")
}

func runMatrix(cmd *cobra.Command, args []string) error {
	// Discover repositories
	repos, err := discover.FindRepositories(".")
	if err != nil {
		return fmt.Errorf("failed to discover repositories: %w", err)
	}

	if len(repos) == 0 {
		fmt.Println("No repositories found")
		return nil
	}

	// Collect all packages from all repositories
	// For now, we'll just create matrix rows based on detected languages
	var matrixRows []matrix.MatrixRow

	for _, repo := range repos {
		languages := detect.DetectLanguages(repo.Path)
		for _, lang := range languages {
			row := matrix.MatrixRow{
				Initiative: repo.Name,
				Channel:    "prod",
				Layer:      getLayer(lang.Language),
				Owner:      "platform",
				Risk:       "medium",
				Status:     "pending",
			}
			matrixRows = append(matrixRows, row)
		}
	}

	// Format as markdown
	output := matrix.FormatMarkdown(matrixRows)

	// Write output
	if matrixOutput != "" {
		if err := os.WriteFile(matrixOutput, []byte(output), 0644); err != nil {
			return fmt.Errorf("failed to write output file: %w", err)
		}
		fmt.Printf("Matrix written to %s\n", matrixOutput)
	} else {
		fmt.Println(output)
	}

	return nil
}

func getLayer(lang interface{}) string {
	langStr := fmt.Sprintf("%v", lang)
	switch langStr {
	case "go":
		return "backend"
	case "typescript":
		return "frontend"
	case "python":
		return "data"
	case "rust":
		return "systems"
	default:
		return "misc"
	}
}
