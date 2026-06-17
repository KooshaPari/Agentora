# Architecture Decision Records

## ADR-001: Workspace Structure for Infrastructure Crates

**Status**: Accepted  
**Date**: 2026-04-02

### Context

Phenotype projects were implementing the same infrastructure concerns repeatedly:
- Error handling
- Configuration management
- Testing utilities
- Validation

This led to code duplication and inconsistent implementations.

### Decision

Create a shared workspace (`phenotype-infrakit`) containing independent infrastructure crates.

### Consequences

- **Positive**: Reduced duplication, consistent implementations
- **Positive**: Centralized maintenance and updates
- **Negative**: Cross-crate dependency management complexity

---

## ADR-002: Hexagonal Architecture for All Crates

**Status**: Accepted  
**Date**: 2026-04-02

### Context

Need to support multiple backends and testing scenarios for each infrastructure concern.

### Decision

All crates follow hexagonal (ports and adapters) architecture:
- **Ports**: Traits defining the interface
- **Adapters**: Concrete implementations
- **Domain**: Core business logic

### Consequences

- **Positive**: Easy to swap implementations
- **Positive**: Testability with mock adapters
- **Negative**: More boilerplate code

---

## ADR-003: No Inter-Crate Dependencies

**Status**: Accepted  
Date: 2026-04-02

### Context

To maximize reusability, each crate should be independently consumable.

### Decision

Crates must not depend on each other. Shared types are duplicated or extracted to a separate contracts crate if needed.

### Consequences

- **Positive**: Each crate can be used standalone
- **Positive**: Clear boundaries between components
- **Negative**: Some type duplication across crates

---

## ADR-004: Rust Edition 2021

**Status**: Accepted  
**Date**: 2026-04-02

### Context

Choosing Rust edition for the workspace.

### Decision

Use Rust Edition 2021 for all crates.

### Consequences

- **Positive**: Modern Rust features available
- **Positive**: Consistent with ecosystem standards

---

## ADR-005: Feature Flags for Optional Dependencies

**Status**: Accepted  
**Date**: 2026-04-02

### Context

Some adapters require heavy dependencies (e.g., `reqwest` for HTTP, `jsonschema` for validation).

### Decision

Use Cargo feature flags to make dependencies optional:
- `reqwest-adapter` for HTTP client
- `schema` for JSON schema validation

### Consequences

- **Positive**: Minimal dependency tree by default
- **Positive**: Users choose needed features
- **Negative**: More complex feature management
