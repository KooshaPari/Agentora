package detect

import (
	"os"
	"path/filepath"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
)

// manifestMap maps manifest filenames to their language and registry.
var manifestMap = []struct {
	Filename string
	Language adapters.Language
	Registry adapters.Registry
}{
	{"Cargo.toml", adapters.LangRust, adapters.RegistryCrates},
	{"pyproject.toml", adapters.LangPython, adapters.RegistryPyPI},
	{"package.json", adapters.LangTypeScript, adapters.RegistryNPM},
	{"go.mod", adapters.LangGo, adapters.RegistryGo},
	{"mix.exs", adapters.LangElixir, adapters.RegistryHex},
	{"build.zig.zon", adapters.LangZig, adapters.RegistryZig},
	{"mojoproject.toml", adapters.LangMojo, adapters.RegistryMojo},
}

// DetectedLanguage holds a detected language and its associated registry.
type DetectedLanguage struct {
	Language     adapters.Language
	Registry     adapters.Registry
	ManifestPath string
}

// DetectLanguages scans a repository path for known manifest files
// and returns all detected languages with their registries.
func DetectLanguages(repoPath string) []DetectedLanguage {
	var detected []DetectedLanguage
	for _, m := range manifestMap {
		p := filepath.Join(repoPath, m.Filename)
		if _, err := os.Stat(p); err == nil {
			detected = append(detected, DetectedLanguage{
				Language:     m.Language,
				Registry:     m.Registry,
				ManifestPath: p,
			})
		}
	}
	return detected
}

// HasLanguage checks if a specific language is detected in the repo.
func HasLanguage(repoPath string, lang adapters.Language) bool {
	for _, d := range DetectLanguages(repoPath) {
		if d.Language == lang {
			return true
		}
	}
	return false
}
