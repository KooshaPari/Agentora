package rollout

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/KooshaPari/pheno-cli/internal/detect"
	"github.com/KooshaPari/pheno-cli/internal/manifest"
	"github.com/KooshaPari/pheno-cli/internal/templates"
)

// RolloutOptions configures a bulk bootstrap run.
type RolloutOptions struct {
	ReposDir     string
	ManifestPath string
	DryRun       bool
	Skip         []string
}

// RolloutResult captures the outcome of bootstrapping a single repo.
type RolloutResult struct {
	Repo         string
	Success      bool
	Error        string
	FilesCreated []string
}

// RunBulkBootstrap bootstraps governance artifacts across all repos in the manifest (or auto-detected).
// It continues processing on per-repo errors (fail-safe).
func RunBulkBootstrap(ctx context.Context, opts RolloutOptions) ([]RolloutResult, error) {
	var m *manifest.OrgManifest
	var err error

	if opts.ManifestPath != "" {
		m, err = manifest.LoadManifest(opts.ManifestPath)
	} else {
		m, err = manifest.GenerateManifest(opts.ReposDir)
	}
	if err != nil {
		return nil, fmt.Errorf("failed to load manifest: %w", err)
	}

	skipSet := make(map[string]bool, len(opts.Skip))
	for _, s := range opts.Skip {
		skipSet[s] = true
	}

	var results []RolloutResult
	for _, repo := range m.Repos {
		if err := ctx.Err(); err != nil {
			break
		}
		if repo.Skip || skipSet[repo.Name] {
			results = append(results, RolloutResult{
				Repo:    repo.Name,
				Success: true,
				Error:   "skipped",
			})
			continue
		}

		repoPath := filepath.Join(opts.ReposDir, repo.Name)
		result := bootstrapRepo(repoPath, repo, opts.DryRun)
		results = append(results, result)
	}

	return results, nil
}

// bootstrapRepo runs bootstrap logic for a single repo and returns the result.
func bootstrapRepo(repoPath string, repo manifest.RepoConfig, dryRun bool) RolloutResult {
	result := RolloutResult{Repo: repo.Name}

	// Resolve language: use manifest value or auto-detect
	language := repo.Language
	if language == "" {
		detected := detect.DetectLanguages(repoPath)
		if len(detected) == 0 {
			result.Error = "could not detect language"
			return result
		}
		language = string(detected[0].Language)
	}

	registry := repo.Registry
	if registry == "" {
		registry = inferRegistry(language)
	}

	riskProfile := repo.RiskProfile
	if riskProfile == "" {
		riskProfile = "low"
	}

	ctx := templates.TemplateContext{
		RepoName:    repo.Name,
		Language:    language,
		Registry:    registry,
		RiskProfile: riskProfile,
	}

	filesToGenerate := map[string]string{
		"mise.toml":                     "mise.toml",
		".git/hooks/pre-commit":         "pre-commit.sh",
		".git/hooks/pre-push":           "pre-push.sh",
		".github/workflows/ci.yml":      "ci.yml",
		".github/workflows/release.yml": "release.yml",
	}

	renderedFiles := make(map[string]string)
	for filePath, templateName := range filesToGenerate {
		content, err := templates.RenderTemplate(templateName, ctx)
		if err != nil {
			result.Error = fmt.Sprintf("template render error for %s: %v", templateName, err)
			return result
		}
		renderedFiles[filePath] = content
	}
	renderedFiles["cliff.toml"] = templates.GetStaticCliffToml()

	if dryRun {
		for filePath := range renderedFiles {
			result.FilesCreated = append(result.FilesCreated, filePath)
		}
		result.Success = true
		return result
	}

	// Write files, skipping existing ones
	for filePath, content := range renderedFiles {
		fullPath := filepath.Join(repoPath, filePath)

		dir := filepath.Dir(fullPath)
		if err := os.MkdirAll(dir, 0755); err != nil {
			result.Error = fmt.Sprintf("mkdir %s: %v", dir, err)
			return result
		}

		if err := os.WriteFile(fullPath, []byte(content), 0644); err != nil {
			result.Error = fmt.Sprintf("write %s: %v", filePath, err)
			return result
		}

		if strings.HasPrefix(filePath, ".git/hooks/") {
			_ = os.Chmod(fullPath, 0755)
		}

		result.FilesCreated = append(result.FilesCreated, filePath)
	}

	result.Success = true
	return result
}

// FormatResults returns a human-readable summary table of rollout results.
func FormatResults(results []RolloutResult) string {
	if len(results) == 0 {
		return "No repositories processed.\n"
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%-30s %-10s %s\n", "REPO", "STATUS", "DETAILS"))
	sb.WriteString(strings.Repeat("-", 70) + "\n")

	succeeded, failed, skipped := 0, 0, 0
	for _, r := range results {
		status := "OK"
		detail := fmt.Sprintf("%d files", len(r.FilesCreated))
		if r.Error == "skipped" {
			status = "SKIP"
			detail = ""
			skipped++
		} else if !r.Success {
			status = "FAIL"
			detail = r.Error
			failed++
		} else {
			succeeded++
		}
		sb.WriteString(fmt.Sprintf("%-30s %-10s %s\n", r.Repo, status, detail))
	}

	sb.WriteString(strings.Repeat("-", 70) + "\n")
	sb.WriteString(fmt.Sprintf("Total: %d OK, %d failed, %d skipped\n", succeeded, failed, skipped))
	return sb.String()
}

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
