# Contributor Quickstart

This guide covers everything needed to build, test, and extend `pheno-cli`.

## Prerequisites

- **Go 1.24+** — [Install Go](https://go.dev/dl/)
- **Git** — version 2.30+
- A target registry account (npm, PyPI, crates.io, etc.) for live publish tests

## Repo Setup

```bash
# Clone the repository
git clone https://github.com/KooshaPari/pheno-cli.git
cd pheno-cli/pheno-cli

# Install dependencies
go mod download

# Verify the build
go build ./...
```

## Building from Source

```bash
# Build the binary
go build -o pheno .

# Install to $GOPATH/bin
go install .

# Cross-compile for Linux amd64
GOOS=linux GOARCH=amd64 go build -o pheno-linux-amd64 .
```

## Running Tests

```bash
# Run all tests
go test ./...

# Run with verbose output
go test -v ./...

# Run a specific package
go test ./internal/adapters/...

# Run with race detector
go test -race ./...

# Run with coverage report
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

## Code Style

- Follow standard Go formatting: `gofmt -w .` or `goimports -w .`
- Run `go vet ./...` before submitting a PR
- Keep packages small and focused; avoid circular imports
- Export only what is needed by other packages

## Adding a New Registry Adapter

Adapters live in `internal/adapters/`. Each adapter implements the `RegistryAdapter` interface defined in `internal/adapters/adapter.go`.

### Step 1: Create the adapter file

Create `internal/adapters/<registry>.go`:

```go
package adapters

import "fmt"

// MyRegistryAdapter implements RegistryAdapter for MyRegistry.
type MyRegistryAdapter struct{}

func (a *MyRegistryAdapter) Name() Registry {
    return RegistryMyRegistry // add the constant to adapter.go
}

func (a *MyRegistryAdapter) Detect(repoPath string) ([]Package, error) {
    // Scan for manifest files (e.g., myregistry.json)
    // Return a Package for each detected publishable unit
    return nil, nil
}

func (a *MyRegistryAdapter) Version(baseVersion string, channel Channel, increment int) (string, error) {
    // Format the pre-release version string for this registry's convention
    // e.g. "1.2.0-alpha.3" or "1.2.0a3"
    return fmt.Sprintf("%s-%s.%d", baseVersion, channel, increment), nil
}

func (a *MyRegistryAdapter) Build(pkg Package) (*BuildResult, error) {
    // Run the registry-specific build command
    // Return the path to the artifact
    return &BuildResult{ArtifactPath: ""}, nil
}

func (a *MyRegistryAdapter) Publish(pkg Package, version string, creds map[string]string) (*PublishResult, error) {
    // Upload the artifact to the registry using creds
    return &PublishResult{RegistryURL: "", Version: version}, nil
}

func (a *MyRegistryAdapter) Verify(pkg Package, version string) (bool, error) {
    // Poll the registry until the version is available, or timeout
    return false, nil
}
```

### Step 2: Register the adapter constants

Add the new registry and language constants to `adapter.go`:

```go
const (
    // existing constants ...
    RegistryMyRegistry Registry = "myregistry"
)
```

### Step 3: Wire up the adapter

Register the adapter in the orchestrator (`internal/publish/orchestrator.go`) so it is included in the adapter lookup map.

### Step 4: Add tests

Create `internal/adapters/<registry>_test.go` covering at minimum:
- `Detect` — returns expected packages for a sample manifest
- `Version` — correct pre-release strings per channel
- `Publish` — mocked HTTP/CLI calls verify correct arguments

### Step 5: Update documentation

- Add a row to the adapter status table in `README.md`
- Add any registry-specific env vars to the configuration table

## Project Layout

```
pheno-cli/
├── main.go                      # Entry point
├── cmd/                         # Cobra commands (publish, promote, audit, ...)
├── internal/
│   ├── adapters/                # Registry adapter implementations
│   │   ├── adapter.go           # RegistryAdapter interface + types
│   │   ├── npm.go               # npm adapter
│   │   └── ...
│   ├── config/                  # Config loading (viper)
│   ├── detect/                  # Repository/manifest detection
│   ├── errors/                  # User-facing error messages
│   ├── publish/                 # Publish orchestration
│   └── version/                 # Version calculation
└── docs/                        # Extended documentation
```

## Submitting a Pull Request

1. Fork the repository and create a feature branch.
2. Make your changes with tests.
3. Run `go build ./... && go test ./... && go vet ./...` — all must pass.
4. Open a PR with a description of what was changed and why.
5. A maintainer will review within 2 business days.
