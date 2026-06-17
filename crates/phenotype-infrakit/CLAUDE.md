# CLAUDE.md - Development Guidelines for phenotype-infrakit

## Project Overview

Rust workspace with infrastructure crates for the Phenotype ecosystem. Each crate is independently consumable.

## Key Directories

- `crates/` - Individual crate directories
  - `phenotype-error-core/` - Error types
  - `phenotype-config-core/` - Configuration
  - `phenotype-health/` - Health checks
  - `phenotype-cache-adapter/` - Caching
  - ... (10+ crates)

## Development Commands

```bash
# Build workspace
cargo build --workspace

# Test workspace
cargo test --workspace

# Check single crate
cargo check -p phenotype-error-core

# Lint
cargo clippy --workspace -- -D warnings

# Document
cargo doc --workspace
```

## Architecture Principles

- **Independence**: No inter-crate dependencies
- **Reusability**: Each crate solves one problem
- **Ergonomics**: Builder patterns, sensible defaults
- **Performance**: Zero-cost abstractions

## Crate Design

```rust
// lib.rs pattern
pub use error::PhenotypeError;
pub use config::ConfigLoader;

mod error;
mod config;

#[cfg(test)]
mod tests;
```

## Phenotype Org Rules

- UTF-8 encoding only
- Worktree discipline: canonical repo stays on `main`
- No agent directories committed
- All tests pass before merging
