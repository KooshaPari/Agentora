package gate

import (
	"encoding/json"
	"fmt"
	"strings"
)

// FormatTable formats a promotion report as a simple text table.
func FormatTable(report *PromotionReport) string {
	var sb strings.Builder

	sb.WriteString("╔════════════════════════════════════════════════════════════════╗\n")
	sb.WriteString(fmt.Sprintf("║ Promotion Report: %s\n", report.PackageName))
	sb.WriteString(fmt.Sprintf("║ %s → %s | Risk Status: ", report.FromChannel, report.ToChannel))
	if report.Passed {
		sb.WriteString("PASSED")
	} else {
		sb.WriteString("FAILED")
	}
	sb.WriteString("\n")
	sb.WriteString("╠════════════════════════════════════════════════════════════════╣\n")

	// Header
	sb.WriteString("║ Gate                           Status    Duration   Errors\n")
	sb.WriteString("║────────────────────────────────────────────────────────────────\n")

	// Rows
	for _, result := range report.Results {
		statusIcon := "✓"
		if !result.Passed {
			statusIcon = "✗"
		}

		gateName := result.CriterionName
		if len(gateName) > 30 {
			gateName = gateName[:27] + "..."
		}

		errorMsg := ""
		if result.Error != "" {
			errorMsg = result.Error
			if len(errorMsg) > 20 {
				errorMsg = errorMsg[:17] + "..."
			}
		}

		sb.WriteString(fmt.Sprintf("║ %-30s %s %6dms   %s\n",
			gateName, statusIcon, result.DurationMs, errorMsg))
	}

	sb.WriteString("╠════════════════════════════════════════════════════════════════╣\n")
	sb.WriteString(fmt.Sprintf("║ Total Duration: %dms | Evaluated: %s\n",
		report.TotalDuration, report.EvaluatedAt.Format("2006-01-02 15:04:05")))
	sb.WriteString("╚════════════════════════════════════════════════════════════════╝\n")

	return sb.String()
}

// FormatJSON formats a promotion report as JSON.
func FormatJSON(report *PromotionReport) (string, error) {
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal report to JSON: %w", err)
	}
	return string(data), nil
}
