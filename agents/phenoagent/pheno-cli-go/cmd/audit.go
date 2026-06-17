package cmd

import (
	"fmt"
	"time"

	"github.com/KooshaPari/pheno-cli/internal/audit"
	"github.com/KooshaPari/pheno-cli/internal/detect"
	"github.com/KooshaPari/pheno-cli/internal/discover"
	"github.com/spf13/cobra"
)

var auditCmd = &cobra.Command{
	Use:   "audit",
	Short: "Audit release status across repositories",
	RunE:  runAudit,
}

var (
	auditReposDir string
	auditRepo     string
	auditFormat   string
)

func init() {
	auditCmd.Flags().StringVar(&auditReposDir, "repos-dir", ".", "Root directory to search for repositories")
	auditCmd.Flags().StringVar(&auditRepo, "repo", "", "Specific repository path (overrides repos-dir)")
	auditCmd.Flags().StringVar(&auditFormat, "format", "table", "Output format: table, json, or csv")
}

func runAudit(cmd *cobra.Command, args []string) error {
	var repos []discover.RepositoryInfo

	// Determine which repositories to audit
	if auditRepo != "" {
		// Single repository mode
		repos = []discover.RepositoryInfo{
			{
				Path:   auditRepo,
				Name:   "specified-repo",
				HasGit: true,
			},
		}
	} else {
		// Discovery mode
		var err error
		repos, err = discover.FindRepositories(auditReposDir)
		if err != nil {
			return fmt.Errorf("failed to discover repositories: %w", err)
		}
		if len(repos) == 0 {
			fmt.Println("No repositories found")
			return nil
		}
	}

	// Build audit report
	startTime := time.Now()
	var results []audit.AuditResult

	for _, repo := range repos {
		// Detect languages in this repository
		languages := detect.DetectLanguages(repo.Path)

		for _, lang := range languages {
			result := audit.AuditResult{
				PackageName: repo.Name,
				Language:    string(lang.Language),
				Registry:    string(lang.Registry),
				Version:     "unknown",
				Status:      "detected",
				RegistryURL: registryURL(lang.Registry),
			}
			results = append(results, result)
		}
	}

	report := &audit.AuditReport{
		Timestamp: startTime,
		Results:   results,
		Duration:  time.Since(startTime),
	}

	// Format and output
	var output string
	var err error

	switch auditFormat {
	case "json":
		output, err = audit.FormatJSON(report)
	case "csv":
		output, err = audit.FormatCSV(report)
	default:
		output = audit.FormatTable(report)
	}

	if err != nil {
		return fmt.Errorf("failed to format output: %w", err)
	}

	fmt.Println(output)
	return nil
}

func registryURL(registry interface{}) string {
	regStr := fmt.Sprintf("%v", registry)
	switch regStr {
	case "npm":
		return "https://registry.npmjs.org"
	case "pypi":
		return "https://pypi.org"
	case "crates.io":
		return "https://crates.io"
	case "go_proxy":
		return "https://proxy.golang.org"
	case "hex.pm":
		return "https://hex.pm"
	case "zig":
		return "https://github.com/ziglang/zig"
	case "mojo":
		return "https://github.com/modularml/mojo"
	default:
		return ""
	}
}
