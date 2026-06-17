# AGENTS.md - Agent Guidelines for phenotype-router-monitor

## Project Identity

- **Name**: phenotype-router-monitor
- **Type**: Rust Library (Router Monitoring)
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-router-monitor`
- **Stack**: Rust, Tokio, Reqwest

## Development Workflow

### Commands

```bash
# Build
cargo build

# Test
cargo test

# Run with example config
cargo run -- --config example.toml

# Lint
cargo clippy -- -D warnings

# Format
cargo fmt
```

### Project Structure

- `src/lib.rs` - Library entry
- `src/monitor.rs` - Core monitoring logic
- `src/api.rs` - API types and endpoints
- `Cargo.toml` - Dependencies

## Code Standards

- **Rust Edition**: 2021
- **Async**: Tokio runtime
- **Errors**: thiserror for custom errors
- **Config**: TOML with serde
- **Tests**: Inline `#[cfg(test)]` modules

## Phenotype Org Rules

- UTF-8 encoding only
- Worktree discipline: canonical repo on `main`
- Zero clippy warnings
- All tests must pass
