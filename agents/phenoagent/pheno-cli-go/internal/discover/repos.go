package discover

import (
	"os"
	"path/filepath"
	"strings"
)

// RepositoryInfo contains metadata about a discovered repository
type RepositoryInfo struct {
	Path   string
	Name   string
	HasGit bool
}

// FindRepositories walks the rootDir up to 3 levels deep and discovers repositories
// It skips node_modules, .git, venv, target, vendor, dist, build, *-wtrees, and hidden directories
func FindRepositories(rootDir string) ([]RepositoryInfo, error) {
	var repos []RepositoryInfo
	skipDirs := map[string]bool{
		"node_modules": true,
		".git":         true,
		"venv":         true,
		"target":       true,
		"vendor":       true,
		"dist":         true,
		"build":        true,
	}

	err := filepath.Walk(rootDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // Skip on error and continue
		}

		// Calculate depth relative to rootDir
		relPath, _ := filepath.Rel(rootDir, path)
		depth := strings.Count(relPath, string(filepath.Separator))
		if depth > 3 {
			return filepath.SkipDir
		}

		if !info.IsDir() {
			return nil
		}

		// Skip hidden directories
		if strings.HasPrefix(info.Name(), ".") && info.Name() != ".git" {
			return filepath.SkipDir
		}

		// Skip specific directories
		if skipDirs[info.Name()] {
			return filepath.SkipDir
		}

		// Skip *-wtrees directories
		if strings.HasSuffix(info.Name(), "-wtrees") {
			return filepath.SkipDir
		}

		// Check if this directory is a repository
		hasGit := false
		gitPath := filepath.Join(path, ".git")
		if stat, err := os.Stat(gitPath); err == nil && stat.IsDir() {
			hasGit = true
		}

		// Check for manifest files (go.mod, package.json, etc.)
		manifestFiles := []string{"go.mod", "package.json", "pyproject.toml", "Cargo.toml", "pom.xml"}
		hasManifest := false
		for _, manifest := range manifestFiles {
			if _, err := os.Stat(filepath.Join(path, manifest)); err == nil {
				hasManifest = true
				break
			}
		}

		// Add if it has git or manifest
		if hasGit || hasManifest {
			repos = append(repos, RepositoryInfo{
				Path:   path,
				Name:   info.Name(),
				HasGit: hasGit,
			})

			// Skip descending into this directory if it's a repo with git
			if hasGit {
				return filepath.SkipDir
			}
		}

		return nil
	})

	return repos, err
}
