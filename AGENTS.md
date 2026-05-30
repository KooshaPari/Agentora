# AGENTS.md — PhenoAgent

## Project Overview

- **Name**: PhenoAgent
- **Description**: Agent API and CLI components for the Phenotype ecosystem - core agent infrastructure
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoAgent`
- **Language Stack**: Rust (primary), Go (components)
- **Published**: Internal (Phenotype ecosystem)

## Quick Start Commands

```bash
# Navigate to PhenoAgent
cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoAgent

# Rust components
cargo build
cargo test

# Go components
cd agentapi && go build ./...
cd pheno-cli && go build .
```

## Architecture

```
PhenoAgent/
├── agentapi/                 # Go-based Agent API
├── CLIProxyAPI/              # CLI proxy API
├── pheno-cli/                # CLI implementation
├── phenotype-agent-core/     # Rust agent core
└── phenotype-daemon/         # Agent daemon
```

## Quality Standards

### Rust Components
- **Line length**: 100 characters
- **Formatter**: `cargo fmt`
- **Linter**: `cargo clippy -- -D warnings`
- **Tests**: `cargo test`

### Go Components
- **Line length**: 100 characters
- **Formatter**: `gofmt`, `goimports`
- **Linter**: `golangci-lint`
- **Tests**: `go test ./...`

## Git Workflow

### Branch Naming
Format: `phenoagent/<type>/<description>` or `<component>/<type>/<description>`

Examples:
- `phenoagent/feat/daemon-v2`
- `pheno-cli/fix/flag-parsing`

### Commit Format
```
<type>(<component>): <description>

Examples:
- feat(agent-core): add async task runner
- fix(pheno-cli): resolve config loading
```

## File Structure

```
PhenoAgent/
├── agentapi/                 # Go API
│   └── go.mod
├── CLIProxyAPI/              # CLI proxy
├── pheno-cli/                # CLI tool
├── phenotype-agent-core/     # Rust core
│   └── Cargo.toml
└── phenotype-daemon/         # Daemon service
```

## CLI Commands

```bash
# Rust
cargo build
cargo test
cargo clippy

# Go
cd agentapi && go build ./...
cd pheno-cli && go build .
go test ./...
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Rust build fails | Check `Cargo.lock` |
| Go build fails | Run `go mod tidy` |
| Cross-component issues | Verify interfaces match |

## Dependencies

- **Rust**: phenotype-agent-core
- **Go**: agentapi, pheno-cli
- **AgilePlus**: Work tracking

## Agent Notes

When working in PhenoAgent:
1. Multiple language components - check which you're modifying
2. Core logic in Rust, APIs in Go
3. CLIProxyAPI may need coordination with cliproxyapi-plusplus
