# Phenotype InfraKit

A Rust workspace containing shared infrastructure crates for the Phenotype ecosystem.

## Overview

Phenotype InfraKit provides standardized infrastructure components that eliminate code duplication across Phenotype projects:

- **Error Handling** - Structured errors with context
- **Configuration** - Type-safe config management
- **Testing** - Test utilities and fixtures
- **Health Checks** - Service health monitoring
- **Validation** - Schema and rule-based validation
- **Rate Limiting** - Token bucket and sliding window algorithms
- **HTTP Client** - Pluggable HTTP client with interceptors

## Quick Start

```bash
# Build all crates
cargo build --workspace

# Run all tests
cargo test --workspace

# Run tests for a specific crate
cargo test -p phenotype-validation
```

## Crates

| Crate | Version | Description |
|-------|---------|-------------|
| `phenotype-config-core` | 0.1.0 | Configuration management abstractions |
| `phenotype-error-core` | 0.1.0 | Error handling types and traits |
| `phenotype-testing` | 0.1.0 | Test utilities and fixtures |
| `phenotype-validation` | 0.1.0 | Schema and rule-based validation |
| `phenotype-rate-limiter` | 0.1.0 | Rate limiting algorithms |
| `phenotype-http-client` | 0.1.0 | HTTP client with pluggable adapters |

## Architecture

All crates follow **hexagonal architecture** (ports and adapters pattern):

```
┌─────────────────────────────────────┐
│         Application Layer          │
├─────────────────────────────────────┤
│          Domain Layer               │
│    Ports (traits/interfaces)        │
├─────────────────────────────────────┤
│         Adapter Layer               │
│    Concrete implementations         │
└─────────────────────────────────────┘
```

## Documentation

- [Journeys](./journeys/) - User journey documentation
- [Reference](./reference/) - Architecture reference
- [Stories](./stories/) - Design stories
- [Audit](./audit/) - Audit reports

## License

MIT
