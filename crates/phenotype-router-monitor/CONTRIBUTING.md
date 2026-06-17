# CONTRIBUTING.md - Contributing to phenotype-router-monitor

## Getting Started

1. Ensure Rust toolchain installed (1.70+)
2. Clone repository
3. Build: `cargo build`
4. Test: `cargo test`

## Development Workflow

### Adding a Route Checker

1. Implement `Checker` trait in `src/checker.rs`
2. Add unit tests
3. Update documentation

### Configuration Changes

1. Update config struct in `src/config.rs`
2. Add serde attributes
3. Test with example TOML

### Code Standards

- `cargo fmt` before committing
- `cargo clippy -- -D warnings` must pass
- All tests pass: `cargo test`
- Documentation tests: `cargo test --doc`

## Testing

```bash
# Unit tests
cargo test

# Integration tests
cargo test --test '*'

# All checks
cargo check && cargo clippy && cargo test
```

## Submitting Changes

1. Create feature branch
2. Make changes with tests
3. Run full test suite
4. Submit PR with description

## License

MIT
