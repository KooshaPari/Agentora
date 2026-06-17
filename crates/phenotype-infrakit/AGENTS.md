# AGENTS.md - Agent Guidelines for phenotype-infrakit

## Project Identity

- **Name**: phenotype-infrakit
- **Type**: Rust Workspace (Infrastructure Crates)
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-infrakit`
- **Stack**: Rust 2021, Tokio

## Development Workflow

### Commands

```bash
# Build all crates
cargo build --workspace

# Test all crates
cargo test --workspace

# Test single crate
cargo test -p phenotype-error-core

# Lint
cargo clippy --workspace -- -D warnings

# Format
cargo fmt

# Docs
cargo doc --workspace --open
```

### Adding a New Crate

1. Create `crates/phenotype-new-crate/`
2. Add `Cargo.toml` with metadata
3. Add to workspace `Cargo.toml`
4. Implement with tests
5. Document with rustdoc

### Project Structure

- `crates/` - Individual crates
- `Cargo.toml` - Workspace definition
- Each crate: `src/`, `Cargo.toml`, `README.md`

## Code Standards

- **Edition**: Rust 2021
- **Lints**: All warnings denied
- **Tests**: Inline `#[cfg(test)]`
- **Docs**: rustdoc for all public items
- **Errors**: thiserror derive macros

## Phenotype Org Rules

- UTF-8 encoding only
- No inter-crate dependencies (each standalone)
- Zero clippy warnings policy
- All public types implement Debug and Clone
