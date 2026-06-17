package adapters

import (
	"bytes"
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

type pyprojectToml struct {
	Project struct {
		Name        string   `toml:"name"`
		Version     string   `toml:"version"`
		Classifiers []string `toml:"classifiers"`
	} `toml:"project"`
	Tool struct {
		Poetry struct {
			Name    string `toml:"name"`
			Version string `toml:"version"`
		} `toml:"poetry"`
	} `toml:"tool"`
}

// PyPIAdapter implements RegistryAdapter for the PyPI registry.
type PyPIAdapter struct{}

func (a *PyPIAdapter) Name() Registry { return RegistryPyPI }

func (a *PyPIAdapter) Detect(repoPath string) ([]Package, error) {
	var packages []Package

	err := filepath.Walk(repoPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() && isExcludedPythonDir(info.Name()) {
			return filepath.SkipDir
		}
		if info.IsDir() || info.Name() != "pyproject.toml" {
			return nil
		}

		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}

		var pyproj pyprojectToml
		if err := toml.Unmarshal(data, &pyproj); err != nil {
			return nil
		}

		name := pyproj.Project.Name
		ver := pyproj.Project.Version
		if name == "" {
			name = pyproj.Tool.Poetry.Name
			ver = pyproj.Tool.Poetry.Version
		}
		if name == "" || ver == "" {
			return nil
		}

		isPrivate := false
		for _, c := range pyproj.Project.Classifiers {
			if c == "Private :: Do Not Upload" {
				isPrivate = true
				break
			}
		}

		packages = append(packages, Package{
			Name:         name,
			Version:      ver,
			ManifestPath: path,
			Registry:     RegistryPyPI,
			Language:     LangPython,
			Private:      isPrivate,
		})
		return nil
	})
	if err != nil {
		return nil, err
	}
	return packages, nil
}

func (a *PyPIAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
	return version.Calculate(baseVersion, string(channel), increment, string(RegistryPyPI))
}

func (a *PyPIAdapter) Build(pkg Package) (*BuildResult, error) {
	pkgDir := filepath.Dir(pkg.ManifestPath)

	cmd := exec.Command("python3", "-m", "build")
	cmd.Dir = pkgDir

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("python build failed: %w: %s", err, stderr.String())
	}

	return &BuildResult{ArtifactPath: filepath.Join(pkgDir, "dist")}, nil
}

func (a *PyPIAdapter) Publish(pkg Package, ver string, creds map[string]string) (*PublishResult, error) {
	pkgDir := filepath.Dir(pkg.ManifestPath)
	distGlob := filepath.Join(pkgDir, "dist", "*")

	args := []string{"upload"}
	matches, _ := filepath.Glob(distGlob)
	args = append(args, matches...)

	env := os.Environ()
	env = append(env, "TWINE_USERNAME=__token__")
	if token, ok := creds["pypi_token"]; ok {
		env = append(env, fmt.Sprintf("TWINE_PASSWORD=%s", token))
	}

	maxRetries := 3
	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		cmd := exec.Command("twine", args...)
		cmd.Dir = pkgDir
		cmd.Env = env

		var stderr bytes.Buffer
		cmd.Stderr = &stderr

		if err := cmd.Run(); err != nil {
			errMsg := stderr.String()
			lastErr = err

			// Idempotent: already published
			if strings.Contains(errMsg, "400") && strings.Contains(errMsg, "already exists") {
				return &PublishResult{
					RegistryURL: fmt.Sprintf("https://pypi.org/project/%s/%s/", pkg.Name, ver),
					Version:     ver,
				}, nil
			}
			if strings.Contains(errMsg, "403") || strings.Contains(errMsg, "Forbidden") {
				return nil, fmt.Errorf("%w: %s", ErrAuth, errMsg)
			}
			if strings.Contains(errMsg, "connection") || strings.Contains(errMsg, "timeout") {
				time.Sleep(time.Duration(5*(attempt+1)) * time.Second)
				continue
			}
			return nil, fmt.Errorf("twine upload failed: %w: %s", err, errMsg)
		}

		return &PublishResult{
			RegistryURL: fmt.Sprintf("https://pypi.org/project/%s/%s/", pkg.Name, ver),
			Version:     ver,
		}, nil
	}
	return nil, fmt.Errorf("%w: max retries exceeded: %v", ErrNetwork, lastErr)
}

func (a *PyPIAdapter) Verify(pkg Package, ver string) (bool, error) {
	normalized := strings.ToLower(strings.ReplaceAll(pkg.Name, "-", "_"))
	url := fmt.Sprintf("https://pypi.org/pypi/%s/%s/json", normalized, ver)
	pollInterval := 10 * time.Second
	deadline := time.Now().Add(5 * time.Minute)

	for time.Now().Before(deadline) {
		resp, err := http.Get(url)
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
		return false, fmt.Errorf("unexpected registry response: %d", resp.StatusCode)
	}
	return false, fmt.Errorf("version %s not available after 5m", ver)
}

func isExcludedPythonDir(name string) bool {
	switch name {
	case "venv", ".venv", "env", ".env", "__pycache__", ".tox",
		".eggs", "build", "dist", ".git", ".mypy_cache", ".pytest_cache":
		return true
	}
	return false
}
