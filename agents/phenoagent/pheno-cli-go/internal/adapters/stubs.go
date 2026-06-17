package adapters

import (
	"fmt"
	"os"
	"path/filepath"

	toml "github.com/pelletier/go-toml/v2"

	"github.com/KooshaPari/pheno-cli/internal/version"
)

// HexAdapter is a pre-wired stub for Hex.pm (Elixir).
type HexAdapter struct{}

func (a *HexAdapter) Name() Registry { return RegistryHex }

func (a *HexAdapter) Detect(repoPath string) ([]Package, error) {
	mixFile := filepath.Join(repoPath, "mix.exs")
	if _, err := os.Stat(mixFile); err != nil {
		return nil, nil
	}
	// mix.exs is Elixir code, not easily parsed from Go.
	// Return a placeholder; full implementation in a future WP.
	return []Package{{
		Name:         filepath.Base(repoPath),
		Version:      "0.0.0",
		ManifestPath: mixFile,
		Registry:     RegistryHex,
		Language:     LangElixir,
	}}, nil
}

func (a *HexAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
	return version.Calculate(baseVersion, string(channel), increment, string(RegistryHex))
}

func (a *HexAdapter) Build(pkg Package) (*BuildResult, error) {
	return nil, fmt.Errorf("%w: hex.pm build not yet implemented", ErrNotSupported)
}

func (a *HexAdapter) Publish(pkg Package, ver string, creds map[string]string) (*PublishResult, error) {
	return nil, fmt.Errorf("%w: hex.pm publish not yet implemented", ErrNotSupported)
}

func (a *HexAdapter) Verify(pkg Package, ver string) (bool, error) {
	return false, fmt.Errorf("%w: hex.pm verify not yet implemented", ErrNotSupported)
}

// ZigAdapter is a pre-wired stub for Zig packages.
type ZigAdapter struct{}

func (a *ZigAdapter) Name() Registry { return RegistryZig }

type zigBuildZon struct {
	Name    string `toml:"name"`
	Version string `toml:"version"`
}

func (a *ZigAdapter) Detect(repoPath string) ([]Package, error) {
	zonFile := filepath.Join(repoPath, "build.zig.zon")
	data, err := os.ReadFile(zonFile)
	if err != nil {
		return nil, nil
	}

	// build.zig.zon is Zig syntax, not TOML. For now, do basic string scanning.
	_ = data
	return []Package{{
		Name:         filepath.Base(repoPath),
		Version:      "0.0.0",
		ManifestPath: zonFile,
		Registry:     RegistryZig,
		Language:     LangZig,
	}}, nil
}

func (a *ZigAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
	return version.Calculate(baseVersion, string(channel), increment, string(RegistryZig))
}

func (a *ZigAdapter) Build(pkg Package) (*BuildResult, error) {
	return nil, fmt.Errorf("%w: zig build not yet implemented", ErrNotSupported)
}

func (a *ZigAdapter) Publish(pkg Package, ver string, creds map[string]string) (*PublishResult, error) {
	return nil, fmt.Errorf("%w: zig publish not yet implemented", ErrNotSupported)
}

func (a *ZigAdapter) Verify(pkg Package, ver string) (bool, error) {
	return false, fmt.Errorf("%w: zig verify not yet implemented", ErrNotSupported)
}

// MojoAdapter is a pre-wired stub for Mojo packages.
type MojoAdapter struct{}

func (a *MojoAdapter) Name() Registry { return RegistryMojo }

type mojoProjectToml struct {
	Project struct {
		Name    string `toml:"name"`
		Version string `toml:"version"`
	} `toml:"project"`
}

func (a *MojoAdapter) Detect(repoPath string) ([]Package, error) {
	mojoFile := filepath.Join(repoPath, "mojoproject.toml")
	data, err := os.ReadFile(mojoFile)
	if err != nil {
		return nil, nil
	}

	var mojo mojoProjectToml
	if err := toml.Unmarshal(data, &mojo); err != nil {
		return nil, nil
	}
	if mojo.Project.Name == "" {
		return nil, nil
	}

	return []Package{{
		Name:         mojo.Project.Name,
		Version:      mojo.Project.Version,
		ManifestPath: mojoFile,
		Registry:     RegistryMojo,
		Language:     LangMojo,
	}}, nil
}

func (a *MojoAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
	return "", fmt.Errorf("%w: mojo versioning not yet supported", ErrNotSupported)
}

func (a *MojoAdapter) Build(pkg Package) (*BuildResult, error) {
	return nil, fmt.Errorf("%w: mojo build not yet implemented", ErrNotSupported)
}

func (a *MojoAdapter) Publish(pkg Package, ver string, creds map[string]string) (*PublishResult, error) {
	return nil, fmt.Errorf("%w: mojo publish not yet implemented", ErrNotSupported)
}

func (a *MojoAdapter) Verify(pkg Package, ver string) (bool, error) {
	return false, fmt.Errorf("%w: mojo verify not yet implemented", ErrNotSupported)
}
