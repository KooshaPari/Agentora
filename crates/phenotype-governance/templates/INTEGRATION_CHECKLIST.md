# Integration Checklist

Step-by-step guide for integrating phenotype shared crates into your project.

## Pre-Integration

- [ ] Read the [Integration Guide](../docs/INTEGRATION_GUIDE.md)
- [ ] Identify which crates you need:
  - `phenotype-bdd` - For BDD testing
  - `phenotype-http-client` - For HTTP requests
  - `phenotype-validation` - For data validation
- [ ] Choose the appropriate template from `phenotype-governance/templates/rust/`

## Adding BDD Tests (phenotype-bdd)

- [ ] Copy `bdd_integration` template to your project
- [ ] Update `Cargo.toml` to add `phenotype-bdd` as dev-dependency
- [ ] Create `tests/features/` directory
- [ ] Write `.feature` files for your domain
- [ ] Create `tests/steps/mod.rs` with step definitions
- [ ] Create `tests/bdd_tests.rs` with test runner
- [ ] Run `cargo test --test bdd_tests`
- [ ] Add CI step to run BDD tests

## Adding HTTP Client (phenotype-http-client)

- [ ] Copy `http_client_integration` template to your project
- [ ] Update `Cargo.toml` to add `phenotype-http-client` as dependency
- [ ] Create `src/api_client.rs` with your API client
- [ ] Use `ReqwestAdapter` for production code
- [ ] Use `MockAdapter` for tests
- [ ] Add `tests/mock_example.rs` with test examples
- [ ] Run `cargo test`

## Adding Validation (phenotype-validation)

- [ ] Copy `validation_integration` template to your project
- [ ] Update `Cargo.toml` to add `phenotype-validation` as dependency
- [ ] Create `src/config.rs` with your configuration structs
- [ ] Add validators for each configuration type
- [ ] Call validation at config load time
- [ ] Add `tests/validation_tests.rs` with validation tests
- [ ] Run `cargo test`

## Post-Integration

- [ ] Update your project README with integration notes
- [ ] Add examples to documentation
- [ ] Run full test suite: `cargo test --all`
- [ ] Run linter: `cargo clippy -- -D warnings`
- [ ] Update CI/CD to include new tests
- [ ] Notify team of new testing capabilities

## Common Issues

### BDD Tests Not Found
- Ensure feature files are in `tests/features/`
- Check file permissions

### HTTP Client Connection Errors
- Check that URL is correct
- Verify network connectivity
- Use MockAdapter for offline testing

### Validation Errors Not Clear
- Add custom error messages with `.with_message()`
- Log validation results for debugging

## Getting Help

- See examples in `phenotype-infrakit/crates/phenotype-bdd/examples/`
- Check integration tests in `phenotype-forge/tests/`
- Reference implementation in `phenotype-sentinel/`
