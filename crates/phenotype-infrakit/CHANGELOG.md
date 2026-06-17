# CHANGELOG.md - phenotype-infrakit

## [Unreleased]

### Added
- Documentation suite (AGENTS.md, CONTRIBUTING.md, PRD.md, ARCHIVED.md, SPEC.md)

## [0.1.0] - 2024

### Added
- phenotype-error-core: Canonical error types
- phenotype-git-core: Git operations
- phenotype-health: Health check abstraction
- phenotype-config-core: Configuration management
- phenotype-telemetry: Observability
- phenotype-validation: Data validation
- phenotype-event-sourcing: Event store
- phenotype-cache-adapter: Two-tier caching
- phenotype-policy-engine: Rule evaluation
- phenotype-state-machine: Generic FSM
- phenotype-contracts: Shared traits

### Design Decisions
- No inter-crate dependencies
- Each crate independently versioned
- Workspace-level dependency management
- thiserror for all error types
- Full rustdoc coverage
