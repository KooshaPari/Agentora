package adapters

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	toml "github.com/pelletier/go-toml/v2"

	"github.com/KooshaPari/pheno-cli/internal/version"
)

type cargoToml struct {
	Package   *cargoPackage `toml:"package"`
	Workspace *struct {
		Members []string `toml:"members"`
	} `toml:"workspace"`
	Dependencies map[string]interface{} `toml:"dependencies"`
}

type cargoPackage struct {
	Name    string `toml:"name"`
	Version string `toml:"version"`
	Publish *bool  `toml:"publish"`
}

// CratesAdapter implements RegistryAdapter for crates.io.
type CratesAdapter struct{}

func (a *CratesAdapter) Name() Registry { return RegistryCrates }

func (a *CratesAdapter) Detect(repoPath string) ([]Package, error) {
	rootPath := filepath.Join(repoPath, "Cargo.toml")
	data, err := os.ReadFile(rootPath)
	if err != nil {
		return nil, nil // No Cargo.toml = not a Rust project
	}

	var root cargoToml
	if err := toml.Unmarshal(data, &root); err != nil {
		return nil, fmt.Errorf("parse Cargo.toml: %w", err)
	}

	// Single crate
	if root.Package != nil && root.Workspace == nil {
		if root.Package.Publish != nil && !*root.Package.Publish {
			return nil, nil
		}
		return []Package{{
			Name:         root.Package.Name,
			Version:      root.Package.Version,
			ManifestPath: rootPath,
			Registry:     RegistryCrates,
			Language:     LangRust,
		}}, nil
	}

	// Workspace
	if root.Workspace != nil {
		return a.detectWorkspace(repoPath, root.Workspace.Members)
	}

	return nil, nil
}

func (a *CratesAdapter) detectWorkspace(repoPath string, patterns []string) ([]Package, error) {
	var packages []Package
	seen := map[string]bool{}

	for _, pattern := range patterns {
		matches, _ := filepath.Glob(filepath.Join(repoPath, pattern))
		for _, dir := range matches {
			manifest := filepath.Join(dir, "Cargo.toml")
			data, err := os.ReadFile(manifest)
			if err != nil {
				continue
			}
			var cargo cargoToml
			if err := toml.Unmarshal(data, &cargo); err != nil || cargo.Package == nil {
				continue
			}
			if seen[cargo.Package.Name] {
				continue
			}
			seen[cargo.Package.Name] = true

			if cargo.Package.Publish != nil && !*cargo.Package.Publish {
				continue
			}

			var deps []string
			for depName, depCfg := range cargo.Dependencies {
				if m, ok := depCfg.(map[string]interface{}); ok {
					if _, hasPath := m["path"]; hasPath {
						deps = append(deps, depName)
					}
				}
			}

			packages = append(packages, Package{
				Name:          cargo.Package.Name,
				Version:       cargo.Package.Version,
				ManifestPath:  manifest,
				Registry:      RegistryCrates,
				Language:      LangRust,
				WorkspaceDeps: deps,
			})
		}
	}
	return packages, nil
}

func (a *CratesAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
	return version.Calculate(baseVersion, string(channel), increment, string(RegistryCrates))
}

func (a *CratesAdapter) Build(pkg Package) (*BuildResult, error) {
	pkgDir := filepath.Dir(pkg.ManifestPath)

	cmd := exec.Command("cargo", "package", "--allow-dirty")
	cmd.Dir = pkgDir

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("cargo package failed: %w: %s", err, stderr.String())
	}

	// Artifact is in target/package/
	return &BuildResult{ArtifactPath: filepath.Join(pkgDir, "target", "package")}, nil
}

func (a *CratesAdapter) Publish(pkg Package, ver string, creds map[string]string) (*PublishResult, error) {
	pkgDir := filepath.Dir(pkg.ManifestPath)

	args := []string{"publish"}
	if token, ok := creds["cargo_token"]; ok {
		args = append(args, "--token", token)
	}

	maxRetries := 5
	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		cmd := exec.Command("cargo", args...)
		cmd.Dir = pkgDir

		var stderr bytes.Buffer
		cmd.Stderr = &stderr

		if err := cmd.Run(); err != nil {
			errMsg := stderr.String()
			lastErr = err

			if strings.Contains(errMsg, "already uploaded") || strings.Contains(errMsg, "already exists") {
				return &PublishResult{
					RegistryURL: fmt.Sprintf("https://crates.io/crates/%s/%s", pkg.Name, ver),
					Version:     ver,
				}, nil
			}
			if strings.Contains(errMsg, "429") || strings.Contains(errMsg, "try again") {
				time.Sleep(time.Duration(30*(attempt+1)) * time.Second)
				continue
			}
			if strings.Contains(errMsg, "403") || strings.Contains(errMsg, "Forbidden") {
				return nil, fmt.Errorf("%w: %s", ErrAuth, errMsg)
			}
			return nil, fmt.Errorf("cargo publish failed: %w: %s", err, errMsg)
		}

		return &PublishResult{
			RegistryURL: fmt.Sprintf("https://crates.io/crates/%s/%s", pkg.Name, ver),
			Version:     ver,
		}, nil
	}
	return nil, fmt.Errorf("%w: max retries exceeded: %v", ErrRateLimited, lastErr)
}

func (a *CratesAdapter) Verify(pkg Package, ver string) (bool, error) {
	url := fmt.Sprintf("https://crates.io/api/v1/crates/%s/%s", pkg.Name, ver)
	pollInterval := 15 * time.Second
	deadline := time.Now().Add(5 * time.Minute)

	client := &http.Client{Timeout: 10 * time.Second}

	for time.Now().Before(deadline) {
		req, _ := http.NewRequest("GET", url, nil)
		req.Header.Set("User-Agent", "pheno-cli (https://github.com/KooshaPari/pheno-cli)")

		resp, err := client.Do(req)
		if err != nil {
			time.Sleep(pollInterval)
			continue
		}
		resp.Body.Close()

		if resp.StatusCode == http.StatusOK {
			return true, nil
		}
		if resp.StatusCode == http.StatusNotFound {
			time.Sleep(pollInterval)
			continue
		}
		return false, fmt.Errorf("unexpected response: %d", resp.StatusCode)
	}
	return false, fmt.Errorf("version %s not available after 5m", ver)
}

// TopoSort returns packages in publish order (dependencies first).
func TopoSort(packages []Package) ([]Package, error) {
	byName := map[string]Package{}
	inDegree := map[string]int{}
	dependents := map[string][]string{}

	for _, pkg := range packages {
		byName[pkg.Name] = pkg
		inDegree[pkg.Name] = 0
	}

	for _, pkg := range packages {
		for _, dep := range pkg.WorkspaceDeps {
			if _, ok := byName[dep]; ok {
				dependents[dep] = append(dependents[dep], pkg.Name)
				inDegree[pkg.Name]++
			}
		}
	}

	var queue []string
	for name, degree := range inDegree {
		if degree == 0 {
			queue = append(queue, name)
		}
	}

	var sorted []Package
	for len(queue) > 0 {
		name := queue[0]
		queue = queue[1:]
		sorted = append(sorted, byName[name])

		for _, dep := range dependents[name] {
			inDegree[dep]--
			if inDegree[dep] == 0 {
				queue = append(queue, dep)
			}
		}
	}

	if len(sorted) != len(packages) {
		return nil, fmt.Errorf("cycle detected in workspace dependencies")
	}
	return sorted, nil
}

// cratesAPIResponse is used for JSON unmarshaling of crates.io API response.
type cratesAPIResponse struct {
	Version struct {
		Num string `json:"num"`
	} `json:"version"`
}

var _ json.Unmarshaler // keep import
