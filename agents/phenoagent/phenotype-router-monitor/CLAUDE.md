# CLAUDE.md - Development Guidelines for phenotype-router-monitor

## Project Overview

Rust library for HTTP router health monitoring with Prometheus metrics export.

## Key Files

- `src/lib.rs` - Library exports
- `src/monitor.rs` - Monitor orchestration
- `src/api.rs` - HTTP API types
- `Cargo.toml` - Workspace dependencies

## Development Commands

```bash
# Build
cargo build

# Test
cargo test

# Check
cargo check

# Clippy
cargo clippy -- -D warnings
```

## Architecture Principles

- **Async-first**: All I/O is async via Tokio
- **Configurable**: TOML-based route configuration
- **Observable**: Prometheus metrics export
- **Ergonomic**: Builder patterns for configuration

## Dependencies

- `tokio` - Async runtime
- `reqwest` - HTTP client
- `serde` - Serialization
- `chrono` - Timestamps
- `thiserror` - Error types

## Phenotype Org Rules

- UTF-8 encoding only
- Worktree discipline: canonical repo stays on `main`
- CI completeness: fix all failures before merging
- Never commit agent directories (`.claude/`, etc.)
