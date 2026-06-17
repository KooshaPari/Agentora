package manifest

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/pelletier/go-toml/v2"
)

// RepoConfig represents the configuration for a single repository in the org manifest.
type RepoConfig struct {
	Name        string `toml:"name"`
	Language    string `toml:"language"`
	Registry    string `toml:"registry"`
	RiskProfile string `toml:"risk_profile"`
	Private     bool   `toml:"private"`
	Skip        bool   `toml:"skip"`
}

// OrgManifest holds the organization-wide repository manifest.
type OrgManifest struct {
	Repos []RepoConfig `toml:"repos"`
}

// LoadManifest reads and parses a repos.toml file at the given path.
func LoadManifest(path string) (*OrgManifest, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read manifest %s: %w", path, err)
	}

	var m OrgManifest
	if err := toml.Unmarshal(data, &m); err != nil {
		return nil, fmt.Errorf("failed to parse manifest %s: %w", path, err)
	}

	return &m, nil
}

// manifestIndicators maps manifest filenames to their likely language.
var manifestIndicators = map[string]string{
	"package.json":     "typescript",
	"Cargo.toml":       "rust",
	"go.mod":           "go",
	"pyproject.toml":   "python",
	"setup.py":         "python",
	"requirements.txt": "python",
}

// registryForLanguage returns the default registry for a language.
func registryForLanguage(lang string) string {
	switch lang {
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

// GenerateManifest auto-detects repositories by scanning reposDir for manifest files.
// It treats each immediate subdirectory that contains a known manifest file as a repo.
func GenerateManifest(reposDir string) (*OrgManifest, error) {
	entries, err := os.ReadDir(reposDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read repos directory %s: %w", reposDir, err)
	}

	var repos []RepoConfig
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		repoPath := filepath.Join(reposDir, entry.Name())
		lang := detectLanguage(repoPath)
		if lang == "" {
			continue
		}
		repos = append(repos, RepoConfig{
			Name:        entry.Name(),
			Language:    lang,
			Registry:    registryForLanguage(lang),
			RiskProfile: "low",
		})
	}

	return &OrgManifest{Repos: repos}, nil
}

// detectLanguage returns the primary language of a repo by checking for manifest files.
func detectLanguage(repoPath string) string {
	// Priority order: go.mod > Cargo.toml > package.json > pyproject.toml
	priority := []string{"go.mod", "Cargo.toml", "package.json", "pyproject.toml", "setup.py", "requirements.txt"}
	for _, name := range priority {
		if _, err := os.Stat(filepath.Join(repoPath, name)); err == nil {
			return manifestIndicators[name]
		}
	}
	return ""
}
