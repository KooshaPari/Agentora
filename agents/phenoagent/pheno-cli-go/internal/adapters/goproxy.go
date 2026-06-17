package adapters

import (
	"bufio"
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/KooshaPari/pheno-cli/internal/version"
)

// GoProxyAdapter implements RegistryAdapter for the Go module proxy.
// Go modules are published via git tags, not registry upload.
type GoProxyAdapter struct{}

func (a *GoProxyAdapter) Name() Registry { return RegistryGo }

func (a *GoProxyAdapter) Detect(repoPath string) ([]Package, error) {
	modFile := filepath.Join(repoPath, "go.mod")
	data, err := os.ReadFile(modFile)
	if err != nil {
		return nil, nil
	}

	scanner := bufio.NewScanner(bytes.NewReader(data))
	var modulePath string
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "module ") {
			modulePath = strings.TrimPrefix(line, "module ")
			break
		}
	}
	if modulePath == "" {
		return nil, nil
	}

	return []Package{{
		Name:         modulePath,
		Version:      "0.0.0-dev",
		ManifestPath: modFile,
		Registry:     RegistryGo,
		Language:     LangGo,
	}}, nil
}

func (a *GoProxyAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
	return version.Calculate(baseVersion, string(channel), increment, string(RegistryGo))
}

// Build for Go is a no-op — publishing happens via git tags.
func (a *GoProxyAdapter) Build(pkg Package) (*BuildResult, error) {
	pkgDir := filepath.Dir(pkg.ManifestPath)

	// Verify the module compiles
	cmd := exec.Command("go", "build", "./...")
	cmd.Dir = pkgDir

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("go build failed: %w: %s", err, stderr.String())
	}

	return &BuildResult{ArtifactPath: pkgDir}, nil
}

// Publish for Go creates a git tag and pushes it. The Go proxy indexes from VCS.
func (a *GoProxyAdapter) Publish(pkg Package, ver string, creds map[string]string) (*PublishResult, error) {
	pkgDir := filepath.Dir(pkg.ManifestPath)

	// Create tag
	tag := ver // Already includes "v" prefix from version calculator
	cmd := exec.Command("git", "tag", tag)
	cmd.Dir = pkgDir
	if out, err := cmd.CombinedOutput(); err != nil {
		if strings.Contains(string(out), "already exists") {
			return &PublishResult{
				RegistryURL: fmt.Sprintf("https://pkg.go.dev/%s@%s", pkg.Name, ver),
				Version:     ver,
			}, nil
		}
		return nil, fmt.Errorf("git tag failed: %w: %s", err, out)
	}

	// Push tag
	cmd = exec.Command("git", "push", "origin", tag)
	cmd.Dir = pkgDir
	if out, err := cmd.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("git push tag failed: %w: %s", err, out)
	}

	return &PublishResult{
		RegistryURL: fmt.Sprintf("https://pkg.go.dev/%s@%s", pkg.Name, ver),
		Version:     ver,
	}, nil
}

func (a *GoProxyAdapter) Verify(pkg Package, ver string) (bool, error) {
	// Request GOPROXY to index the version
	url := fmt.Sprintf("https://proxy.golang.org/%s/@v/%s.info", pkg.Name, ver)
	deadline := time.Now().Add(5 * time.Minute)
	pollInterval := 15 * time.Second

	for time.Now().Before(deadline) {
		cmd := exec.Command("go", "list", "-m", fmt.Sprintf("%s@%s", pkg.Name, ver))
		if err := cmd.Run(); err == nil {
			return true, nil
		}
		time.Sleep(pollInterval)
	}
	_ = url // used conceptually; actual check is via go list
	return false, fmt.Errorf("version %s not indexed after 5m", ver)
}
