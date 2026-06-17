package adapters

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/KooshaPari/pheno-cli/internal/version"
)

type npmPackageJSON struct {
	Name         string            `json:"name"`
	Version      string            `json:"version"`
	Private      bool              `json:"private"`
	Workspaces   []string          `json:"workspaces,omitempty"`
	Dependencies map[string]string `json:"dependencies,omitempty"`
}

// NpmAdapter implements RegistryAdapter for the npm registry.
type NpmAdapter struct{}

func (a *NpmAdapter) Name() Registry { return RegistryNPM }

func (a *NpmAdapter) Detect(repoPath string) ([]Package, error) {
	var packages []Package

	err := filepath.Walk(repoPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() && isExcludedDir(info.Name()) {
			return filepath.SkipDir
		}
		if info.IsDir() || info.Name() != "package.json" {
			return nil
		}

		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}

		var pj npmPackageJSON
		if err := json.Unmarshal(data, &pj); err != nil {
			return nil
		}
		if pj.Name == "" || pj.Version == "" {
			return nil
		}

		packages = append(packages, Package{
			Name:         pj.Name,
			Version:      pj.Version,
			ManifestPath: path,
			Registry:     RegistryNPM,
			Language:     LangTypeScript,
			Private:      pj.Private,
		})
		return nil
	})
	if err != nil {
		return nil, err
	}
	return packages, nil
}

func (a *NpmAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
	return version.Calculate(baseVersion, string(channel), increment, string(RegistryNPM))
}

func (a *NpmAdapter) Build(pkg Package) (*BuildResult, error) {
	pkgDir := filepath.Dir(pkg.ManifestPath)
	tmpDir := os.TempDir()

	cmd := exec.Command("npm", "pack", "--pack-destination", tmpDir)
	cmd.Dir = pkgDir

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("npm pack failed: %w: %s", err, stderr.String())
	}

	tarball := strings.TrimSpace(stdout.String())
	lines := strings.Split(tarball, "\n")
	filename := lines[len(lines)-1]

	return &BuildResult{ArtifactPath: filepath.Join(tmpDir, filename)}, nil
}

func (a *NpmAdapter) Publish(pkg Package, ver string, creds map[string]string) (*PublishResult, error) {
	distTag := version.DistTag(string(ChannelProd))
	for _, ch := range []Channel{ChannelAlpha, ChannelCanary, ChannelBeta, ChannelRC} {
		if strings.Contains(ver, string(ch)) {
			distTag = version.DistTag(string(ch))
			break
		}
	}

	pkgDir := filepath.Dir(pkg.ManifestPath)
	args := []string{"publish", "--tag", distTag}
	if pkg.Name[0] == '@' {
		args = append(args, "--access", "public")
	}

	env := os.Environ()
	if token, ok := creds["npm_token"]; ok {
		env = append(env, fmt.Sprintf("npm_config_//registry.npmjs.org/:_authToken=%s", token))
	}

	maxRetries := 5
	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		cmd := exec.Command("npm", args...)
		cmd.Dir = pkgDir
		cmd.Env = env

		var stderr bytes.Buffer
		cmd.Stderr = &stderr

		if err := cmd.Run(); err != nil {
			errMsg := stderr.String()
			lastErr = err

			if strings.Contains(errMsg, "429") || strings.Contains(errMsg, "too many requests") {
				sleep := parseRetryAfter(errMsg, 60*time.Second)
				time.Sleep(sleep)
				continue
			}
			if strings.Contains(errMsg, "403") || strings.Contains(errMsg, "Forbidden") {
				return nil, fmt.Errorf("%w: %s", ErrAuth, errMsg)
			}
			if strings.Contains(errMsg, "EOTP") || strings.Contains(errMsg, "one-time password") {
				return nil, fmt.Errorf("%w: EOTP required — use granular access token with 2FA bypass", ErrAuth)
			}
			if strings.Contains(errMsg, "previously published") || strings.Contains(errMsg, "cannot publish over") {
				return nil, fmt.Errorf("%w: %s", ErrAlreadyPublished, errMsg)
			}
			return nil, fmt.Errorf("npm publish failed: %w: %s", err, errMsg)
		}

		return &PublishResult{
			RegistryURL: fmt.Sprintf("https://www.npmjs.com/package/%s/v/%s", pkg.Name, ver),
			Version:     ver,
		}, nil
	}
	return nil, fmt.Errorf("%w: max retries exceeded: %v", ErrRateLimited, lastErr)
}

func (a *NpmAdapter) Verify(pkg Package, ver string) (bool, error) {
	url := fmt.Sprintf("https://registry.npmjs.org/%s/%s", pkg.Name, ver)
	pollInterval := 10 * time.Second
	maxWait := 5 * time.Minute
	deadline := time.Now().Add(maxWait)

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
	return false, fmt.Errorf("version %s not available after %v", ver, maxWait)
}

func isExcludedDir(name string) bool {
	switch name {
	case "node_modules", ".git", "dist", "build", ".next", ".nuxt":
		return true
	}
	return name != "" && name[0] == '.'
}

func parseRetryAfter(errMsg string, defaultDuration time.Duration) time.Duration {
	for _, line := range strings.Split(errMsg, "\n") {
		if strings.Contains(line, "retry after") {
			parts := strings.Fields(line)
			for i, part := range parts {
				if part == "after" && i+1 < len(parts) {
					if seconds, err := strconv.Atoi(parts[i+1]); err == nil {
						return time.Duration(seconds) * time.Second
					}
				}
			}
		}
	}
	return defaultDuration
}
