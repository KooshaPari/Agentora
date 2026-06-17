# BDD Integration Template

This template shows how to integrate `phenotype-bdd` into your Rust project.

## Files

- `Cargo.toml` - Dependencies
- `tests/features/example.feature` - Sample Gherkin feature file
- `tests/steps/mod.rs` - Step definitions
- `tests/bdd_tests.rs` - Test runner

## Quick Start

1. Copy these files to your project
2. Customize the feature files for your domain
3. Implement the step definitions
4. Run with `cargo test`

## Customization

Replace the example domain ("Login") with your actual domain concepts.

## Running Tests

```bash
cargo test --test bdd_tests
```

## Adding More Features

Create additional `.feature` files in `tests/features/` and add corresponding step definitions.
