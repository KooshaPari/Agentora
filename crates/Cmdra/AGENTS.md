# AGENTS.md - Cmdra

## Project Overview

- **Name**: clikit (published as Cmdra)
- **Description**: Universal CLI framework with hexagonal architecture and plugin support
- **Language**: Rust (edition 2021)
- **Location**: Phenotype repos shelf

## Architecture

- **Hexagonal Architecture**: Clean separation of domain logic from infrastructure
- **Plugin System**: Extensible command and output adapters
- **Structured Output**: JSON, YAML, TOML, and custom formatters

## Agent Rules

### Project-Specific Rules

1. **Hexagonal Structure**
   ```
   src/
   ├── domain/           # Pure domain (no external deps)
   ├── application/      # Use cases
   ├── adapters/         # Port implementations
   │   ├── primary/     # Driving adapters
   │   └── secondary/   # Driven adapters
   └── infrastructure/   # Cross-cutting
   ```

2. **xDD Methodologies**
   - TDD, BDD, DDD, ATDD, SDD in development
   - SOLID, DRY, KISS, YAGNI in design
   - Property-Based Testing for complex logic
   - Mutation Testing for coverage

3. **Code Style**
   - Run `cargo fmt` before committing
   - Max 50 lines per function
   - Document public APIs with doc comments
   - Self-documenting code

### Phenotype Org Standard Rules

1. **UTF-8 encoding** in all text files
2. **Worktree discipline**: canonical repo stays on `main`
3. **CI completeness**: fix all CI failures before merging
4. **Never commit** agent directories (`.claude/`, `.codex/`, `.cursor/`)

## Quality Standards

```bash
# Build
cargo build

# Test
cargo test

# Lint
cargo clippy -- -D warnings

# Format
cargo fmt --check
```

## Git Workflow

1. Create feature branch: `git checkout -b feat/my-feature`
2. Add tests
3. Ensure all tests pass
4. Run linting
5. Commit using conventional commits
6. Push and create PR
