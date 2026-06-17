# SPECIFICATION: Phenotype InfraKit

## Overview

Rust workspace containing generic infrastructure crates extracted from the Phenotype ecosystem.

## Architecture

### Crate Organization

```
crates/
├── phenotype-error-core/      # Canonical error types
├── phenotype-git-core/        # Git operations
├── phenotype-health/          # Health check abstraction
├── phenotype-config-core/     # Configuration management
├── phenotype-telemetry/       # Observability infrastructure
├── phenotype-validation/      # Data validation
├── phenotype-event-sourcing/  # Event store with hash chains
├── phenotype-cache-adapter/   # LRU + DashMap cache
├── phenotype-policy-engine/   # Rule-based policies
├── phenotype-state-machine/  # Generic FSM
└── phenotype-contracts/       # Shared traits/types
```

## Crate Specifications

### phenotype-error-core

Canonical error types using `thiserror`:

```rust
#[derive(Error, Debug)]
pub enum PhenotypeError {
    #[error("validation failed: {0}")]
    Validation(String),
    #[error("configuration error: {0}")]
    Config(String),
}
```

### phenotype-cache-adapter

Two-tier caching:
- LRU cache for hot data
- DashMap for concurrent access
- TTL support for expiration

### phenotype-policy-engine

Rule evaluation with TOML configuration:

```toml
[[policies]]
name = "rate_limit"
type = "rate_limit"
max_requests = 100
window_seconds = 60
```

## Dependencies

Workspace-level management:
- `serde` - Serialization
- `thiserror` - Error handling
- `tokio` - Async runtime
- `dashmap` - Concurrent hashmap
- `lru` - LRU cache

## Build Configuration

```toml
[workspace]
members = ["crates/*"]
resolver = "2"

[workspace.dependencies]
serde = { version = "1", features = ["derive"] }
thiserror = "1"
tokio = { version = "1", features = ["full"] }
```

## Usage

```rust
use phenotype_error_core::PhenotypeError;
use phenotype_config_core::ConfigLoader;

let config = ConfigLoader::new().load("config.toml")?;
```
