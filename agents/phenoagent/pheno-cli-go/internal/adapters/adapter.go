package adapters

import "errors"

// Sentinel errors for adapter operations.
var (
	ErrRateLimited      = errors.New("registry rate limited")
	ErrAuth             = errors.New("authentication failed")
	ErrNetwork          = errors.New("network error")
	ErrAlreadyPublished = errors.New("version already published")
	ErrPrivatePackage   = errors.New("package is private")
	ErrDirtyWorkTree    = errors.New("working tree is dirty")
	ErrNotSupported     = errors.New("operation not supported for this registry")
)

// Registry identifies a package registry.
type Registry string

const (
	RegistryNPM    Registry = "npm"
	RegistryPyPI   Registry = "pypi"
	RegistryCrates Registry = "crates.io"
	RegistryGo     Registry = "go_proxy"
	RegistryHex    Registry = "hex.pm"
	RegistryZig    Registry = "zig"
	RegistryMojo   Registry = "mojo"
)

// Language identifies a programming language.
type Language string

const (
	LangRust       Language = "rust"
	LangPython     Language = "python"
	LangTypeScript Language = "typescript"
	LangGo         Language = "go"
	LangElixir     Language = "elixir"
	LangZig        Language = "zig"
	LangMojo       Language = "mojo"
)

// Channel represents a release channel tier.
type Channel string

const (
	ChannelAlpha  Channel = "alpha"
	ChannelCanary Channel = "canary"
	ChannelBeta   Channel = "beta"
	ChannelRC     Channel = "rc"
	ChannelProd   Channel = "prod"
)

// ChannelOrdinal returns the numeric tier for a channel (0=alpha, 4=prod).
func ChannelOrdinal(ch Channel) int {
	switch ch {
	case ChannelAlpha:
		return 0
	case ChannelCanary:
		return 1
	case ChannelBeta:
		return 2
	case ChannelRC:
		return 3
	case ChannelProd:
		return 4
	default:
		return -1
	}
}

// Package represents a publishable unit detected from a manifest.
type Package struct {
	Name          string
	Version       string
	ManifestPath  string
	Registry      Registry
	Language      Language
	Private       bool
	WorkspaceDeps []string
}

// BuildResult contains the output of a build operation.
type BuildResult struct {
	ArtifactPath string
}

// PublishResult contains the output of a publish operation.
type PublishResult struct {
	RegistryURL string
	Version     string
}

// RegistryAdapter defines the interface for interacting with a package registry.
type RegistryAdapter interface {
	// Detect scans a repository path and returns all publishable packages.
	Detect(repoPath string) ([]Package, error)

	// Version calculates the registry-specific pre-release version string.
	Version(baseVersion string, channel Channel, increment int) (string, error)

	// Build creates the package artifact for publishing.
	Build(pkg Package) (*BuildResult, error)

	// Publish uploads the built artifact to the registry.
	Publish(pkg Package, version string, creds map[string]string) (*PublishResult, error)

	// Verify confirms the published version is available on the registry.
	Verify(pkg Package, version string) (bool, error)

	// Name returns the registry name.
	Name() Registry
}
