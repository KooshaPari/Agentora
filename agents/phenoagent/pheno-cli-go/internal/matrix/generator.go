package matrix

import (
	"fmt"
	"strings"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
)

// MatrixRow represents a single row in the release matrix
type MatrixRow struct {
	Initiative string
	Channel    string
	Layer      string
	Owner      string
	Risk       string
	Status     string
}

// GenerateMatrix creates matrix rows from a list of packages
func GenerateMatrix(packages []adapters.Package) []MatrixRow {
	var rows []MatrixRow

	for _, pkg := range packages {
		row := MatrixRow{
			Initiative: pkg.Name,
			Channel:    "prod",
			Layer:      determineLayer(pkg.Language),
			Owner:      "platform",
			Risk:       determineRisk(pkg.Private),
			Status:     "pending",
		}
		rows = append(rows, row)
	}

	return rows
}

// determineLayer returns the layer based on language
func determineLayer(lang adapters.Language) string {
	switch lang {
	case adapters.LangGo:
		return "backend"
	case adapters.LangTypeScript:
		return "frontend"
	case adapters.LangPython:
		return "data"
	case adapters.LangRust:
		return "systems"
	default:
		return "misc"
	}
}

// determineRisk returns the risk level based on package attributes
func determineRisk(isPrivate bool) string {
	if isPrivate {
		return "low"
	}
	return "medium"
}

// FormatMarkdown returns a markdown table of matrix rows
func FormatMarkdown(rows []MatrixRow) string {
	if len(rows) == 0 {
		return "No packages in matrix"
	}

	var builder strings.Builder

	// Header
	builder.WriteString("| Initiative | Channel | Layer | Owner | Risk | Status |\n")
	builder.WriteString("|---|---|---|---|---|---|\n")

	// Rows
	for _, row := range rows {
		builder.WriteString(fmt.Sprintf(
			"| %s | %s | %s | %s | %s | %s |\n",
			row.Initiative,
			row.Channel,
			row.Layer,
			row.Owner,
			row.Risk,
			row.Status,
		))
	}

	return builder.String()
}
