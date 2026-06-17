# CONTRIBUTING.md - Contributing to phenotype-infrakit

## Getting Started

1. Install Rust toolchain (1.70+)
2. Clone repository
3. Build: `cargo build --workspace`
4. Test: `cargo test --workspace`

## Development Workflow

### Adding a New Crate

1. Create directory: `crates/phenotype-<name>/`
2. Add `Cargo.toml`:
```toml
[package]
name = "phenotype-<name>"
version.workspace = true
edition.workspace = true
```
3. Create `src/lib.rs`
4. Add to workspace `Cargo.toml` members list
5. Write tests
6. Document with rustdoc

### Code Standards

- `cargo fmt` before committing
- `cargo clippy --workspace -- -D warnings` must pass
- All tests pass: `cargo test --workspace`
- Doc tests: `cargo test --doc --workspace`

### Testing

```bash
# Unit tests
cargo test --workspace

# Single crate
cargo test -p phenotype-error-core

# With output
cargo test --workspace -- --nocapture
```

### Documentation

- All public items must have rustdoc
- Include examples in docs
- README.md per crate

## Submitting Changes

1. Create feature branch
2. Make changes with tests
3. Run full check: `cargo fmt && cargo clippy && cargo test`
4. Submit PR

## License

MIT
