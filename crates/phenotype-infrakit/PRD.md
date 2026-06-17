# Product Requirements: Phenotype InfraKit

## Purpose

Provide shared, reusable infrastructure components for all Phenotype services to ensure consistency and reduce duplication.

## User Stories

### US-1: Error Handling
As a developer, I want standardized error types so that errors propagate consistently across services.

**Acceptance Criteria:**
- Common error enum with `thiserror`
- HTTP status code mapping
- Serializable for JSON responses

### US-2: Configuration
As an operator, I want unified config loading so that all services use the same patterns.

**Acceptance Criteria:**
- TOML/YAML/JSON support
- Environment variable override
- Validation on load

### US-3: Caching
As a developer, I want a ready-to-use cache so that I don't reimplement caching.

**Acceptance Criteria:**
- Two-tier LRU + concurrent map
- TTL support
- Hit/miss metrics

### US-4: Health Checks
As an SRE, I want standardized health check patterns so that monitoring is consistent.

**Acceptance Criteria:**
- Health trait for components
- Aggregated health endpoints
- Custom health checks

## Features

| Priority | Crate | Description |
|----------|-------|-------------|
| P0 | error-core | Canonical error types |
| P0 | config-core | Configuration loading |
| P0 | health | Health check abstraction |
| P1 | cache-adapter | LRU + DashMap caching |
| P1 | validation | Data validation |
| P1 | telemetry | Observability |
| P2 | event-sourcing | Append-only event store |
| P2 | policy-engine | Rule evaluation |
| P2 | state-machine | FSM with guards |
| P2 | contracts | Shared traits |

## Non-Functional Requirements

- **Zero Dependencies**: Each crate standalone
- **Async-Ready**: Tokio-compatible
- **Typed**: Full type safety
- **Documented**: rustdocs for all public APIs

## Success Metrics

- Used by 100% of Phenotype services
- < 100 KB per crate (optimized)
- Zero clippy warnings
- 100% doc coverage

## Timeline

Continuous delivery - crates added as needs emerge.
