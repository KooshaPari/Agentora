package audit

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// AuditResult represents a single audit result for a package
type AuditResult struct {
	PackageName string
	Language    string
	Registry    string
	Version     string
	Status      string
	RegistryURL string
}

// AuditReport contains the complete audit results
type AuditReport struct {
	Timestamp time.Time
	Results   []AuditResult
	Duration  time.Duration
}

// FormatTable returns a formatted text table of audit results
func FormatTable(report *AuditReport) string {
	if len(report.Results) == 0 {
		return "No packages found"
	}

	// Calculate column widths
	packageWidth := 15
	languageWidth := 12
	registryWidth := 12
	versionWidth := 12
	statusWidth := 10

	for _, r := range report.Results {
		if len(r.PackageName) > packageWidth {
			packageWidth = len(r.PackageName)
		}
		if len(r.Language) > languageWidth {
			languageWidth = len(r.Language)
		}
		if len(r.Registry) > registryWidth {
			registryWidth = len(r.Registry)
		}
		if len(r.Version) > versionWidth {
			versionWidth = len(r.Version)
		}
		if len(r.Status) > statusWidth {
			statusWidth = len(r.Status)
		}
	}

	var builder strings.Builder

	// Header
	builder.WriteString(fmt.Sprintf(
		"%-*s | %-*s | %-*s | %-*s | %-*s\n",
		packageWidth, "PACKAGE",
		languageWidth, "LANGUAGE",
		registryWidth, "REGISTRY",
		versionWidth, "VERSION",
		statusWidth, "STATUS",
	))

	// Separator
	builder.WriteString(strings.Repeat("-", packageWidth+languageWidth+registryWidth+versionWidth+statusWidth+12))
	builder.WriteString("\n")

	// Rows
	for _, r := range report.Results {
		builder.WriteString(fmt.Sprintf(
			"%-*s | %-*s | %-*s | %-*s | %-*s\n",
			packageWidth, r.PackageName,
			languageWidth, r.Language,
			registryWidth, r.Registry,
			versionWidth, r.Version,
			statusWidth, r.Status,
		))
	}

	return builder.String()
}

// FormatJSON returns the audit report as JSON
func FormatJSON(report *AuditReport) (string, error) {
	data := map[string]interface{}{
		"timestamp": report.Timestamp,
		"results":   report.Results,
		"duration":  report.Duration.String(),
	}

	bytes, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return "", err
	}

	return string(bytes), nil
}

// FormatCSV returns the audit report as CSV
func FormatCSV(report *AuditReport) (string, error) {
	var builder strings.Builder
	writer := csv.NewWriter(&builder)

	// Write header
	header := []string{"PACKAGE", "LANGUAGE", "REGISTRY", "VERSION", "STATUS", "REGISTRY_URL"}
	if err := writer.Write(header); err != nil {
		return "", err
	}

	// Write rows
	for _, r := range report.Results {
		row := []string{
			r.PackageName,
			r.Language,
			r.Registry,
			r.Version,
			r.Status,
			r.RegistryURL,
		}
		if err := writer.Write(row); err != nil {
			return "", err
		}
	}

	writer.Flush()
	if err := writer.Error(); err != nil {
		return "", err
	}

	return builder.String(), nil
}
