# Cmdra - Rust CLI tool
# Native task runner (just)

# Default recipe
default: help

# Help
help:
  @echo "Cmdra - Rust CLI tool"
  @echo ""
  @just --list

# Quality checks
check: fmt clippy test
  @echo "All checks passed!"

# Format code
fmt:
  cargo fmt --all

# Lint
clippy:
  cargo clippy --workspace -- -D warnings

# Run tests
test:
  cargo test --workspace

# Build
build:
  cargo build --release

# Run CLI
dev:
  cargo run --bin cmdra --watch

# Clean
clean:
  cargo clean

# Benchmarks
bench:
  cargo bench --workspace
