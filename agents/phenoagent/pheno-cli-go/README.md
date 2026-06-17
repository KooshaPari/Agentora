# pheno – Release Governance CLI

`pheno` is the org-wide release governance and developer experience CLI for Phenotype repositories. It automates publishing, promotion, auditing, and governance artifact bootstrapping across multiple package registries.

## Installation

### Go Install

```bash
go install github.com/KooshaPari/pheno-cli@latest
```

### Binary Download

Pre-built binaries are available from the releases page for Linux (amd64, arm64), macOS (amd64, arm64), and Windows (amd64).

```bash
# macOS (Apple Silicon)
curl -L https://github.com/KooshaPari/pheno-cli/releases/latest/download/pheno-darwin-arm64 -o /usr/local/bin/pheno
chmod +x /usr/local/bin/pheno
```

## Quick Start (5-Minute Bootstrap to Publish)

```bash
# 1. Bootstrap governance artifacts for your repo
pheno bootstrap --repo .

# 2. Publish to alpha channel
pheno publish --channel alpha --version 0.1.0

# 3. Promote from alpha to canary after validation
pheno promote --from alpha --to canary --version 0.1.0

# 4. Check release audit trail
pheno audit --repo .

# 5. View release matrix across channels
pheno matrix
```

## Commands Reference

### `pheno publish`

Publish packages to one or more channels.

```
Usage:
  pheno publish [flags]

Flags:
  --channel string    Target release channel (alpha|canary|beta|rc|prod) (default "alpha")
  --version string    Semantic version to publish (e.g. 1.2.3)
  --dry-run           Simulate without writing to registry
  --repo string       Repository path (default: current directory)
  --registry string   Target a specific registry (npm|pypi|crates.io|go|hex|zig|mojo)
  -h, --help          Help for publish
```

**Examples:**

```bash
# Publish all detected packages to alpha
pheno publish --channel alpha --version 1.0.0

# Dry run to preview what would be published
pheno publish --channel beta --version 1.0.0 --dry-run

# Publish only the npm package
pheno publish --channel prod --version 1.0.0 --registry npm
```

### `pheno promote`

Promote a release from one channel to the next.

```
Usage:
  pheno promote [flags]

Flags:
  --from string       Source channel (alpha|canary|beta|rc)
  --to string         Target channel (canary|beta|rc|prod)
  --version string    Version to promote
  --repo string       Repository path (default: current directory)
  --force             Skip gate checks (use with caution)
  -h, --help          Help for promote
```

**Examples:**

```bash
# Promote 1.0.0 from beta to rc
pheno promote --from beta --to rc --version 1.0.0

# Promote to prod (triggers full gate evaluation)
pheno promote --from rc --to prod --version 1.0.0
```

### `pheno audit`

Audit release status and history across channels.

```
Usage:
  pheno audit [flags]

Flags:
  --repo string       Repository path (default: current directory)
  --channel string    Filter by channel
  --format string     Output format (table|json|yaml) (default "table")
  -h, --help          Help for audit
```

**Examples:**

```bash
# Full audit of current repo
pheno audit

# Audit only prod releases in JSON format
pheno audit --channel prod --format json
```

### `pheno matrix`

Generate a release matrix showing version status across all channels.

```
Usage:
  pheno matrix [flags]

Flags:
  --repo string       Repository path (default: current directory)
  --format string     Output format (table|json) (default "table")
  -h, --help          Help for matrix
```

**Examples:**

```bash
# Display release matrix table
pheno matrix

# Output matrix as JSON for CI consumption
pheno matrix --format json
```

### `pheno bootstrap`

Bootstrap governance artifacts (release config, channel definitions, CI workflows) for a repository.

```
Usage:
  pheno bootstrap [flags]

Flags:
  --repo string       Repository path to bootstrap (default: current directory)
  --template string   Governance template to use (default "standard")
  --force             Overwrite existing artifacts
  -h, --help          Help for bootstrap
```

**Examples:**

```bash
# Bootstrap a new repo with standard governance
pheno bootstrap --repo ./my-package

# Re-bootstrap with force (overwrites existing config)
pheno bootstrap --force
```

### `pheno config`

Manage CLI configuration.

```
Usage:
  pheno config [command]

Available Commands:
  get         Get a config value
  set         Set a config value
  list        List all config values

Flags:
  -h, --help  Help for config
```

**Examples:**

```bash
# List all current configuration
pheno config list

# Set npm token
pheno config set npm_token <your-token>
```

## Configuration

### Config File

The default config file is `~/.config/pheno/config.toml`.

```toml
# ~/.config/pheno/config.toml

[npm]
token = "npm_xxxxxxxxxxxx"
registry = "https://registry.npmjs.org"

[pypi]
token = "pypi-xxxxxxxxxxxx"
repository = "https://upload.pypi.org/legacy/"

[crates]
token = "xxxxxxxxxxxxxxxx"

[go]
proxy = "https://proxy.golang.org"

[hex]
api_key = ""

[defaults]
channel = "alpha"
dry_run = false
```

A custom config file path can be passed with `--config`:

```bash
pheno publish --config /path/to/custom-config.toml --channel alpha --version 1.0.0
```

### Environment Variables

All configuration values can be overridden with environment variables using the `PHENO_` prefix:

| Variable              | Description                        |
|-----------------------|------------------------------------|
| `PHENO_NPM_TOKEN`     | npm registry authentication token |
| `PHENO_PYPI_TOKEN`    | PyPI API token                     |
| `PHENO_CRATES_TOKEN`  | crates.io API token                |
| `PHENO_GO_PROXY`      | Go module proxy URL                |
| `PHENO_HEX_API_KEY`   | Hex.pm API key                     |
| `PHENO_DRY_RUN`       | Set to `true` to enable dry-run globally |

## Adapter Status

| Registry    | Status  | Languages          | Notes                              |
|-------------|---------|--------------------|------------------------------------|
| npm         | ✓       | TypeScript, JS     | Full publish, promote, verify      |
| PyPI        | ✓       | Python             | Full publish, promote, verify      |
| crates.io   | ✓       | Rust               | Full publish, promote, verify      |
| Go          | ✓       | Go                 | Tag-based, proxy propagation check |
| Hex.pm      | stub    | Elixir             | Detect only, publish pending       |
| Zig         | stub    | Zig                | Detect only, publish pending       |
| Mojo        | stub    | Mojo               | Detect only, publish pending       |

## Global Flags

The following flags are available on all commands:

| Flag        | Description                                      |
|-------------|--------------------------------------------------|
| `--config`  | Path to config file (default: ~/.config/pheno/config.toml) |
| `--verbose` | Enable verbose output                            |
| `--help`    | Show help for any command                        |
