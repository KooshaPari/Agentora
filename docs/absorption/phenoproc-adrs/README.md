# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for PhenoProc.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs are stored in source control alongside the code they describe, ensuring documentation remains synchronized with implementation.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](ADR-001-async-first-process-management.md) | Async-First Process Management Architecture | Accepted | 2026-04-04 |
| [ADR-002](ADR-002-command-deduplication-strategy.md) | Command Deduplication via Content-Addressed Cache | Accepted | 2026-04-04 |
| [ADR-003](ADR-003-workspace-crate-organization.md) | Five-Crate Workspace Organization | Accepted | 2026-04-04 |

## Status Definitions

- **Proposed**: Under consideration, seeking feedback
- **Accepted**: Approved for implementation
- **Deprecated**: No longer applicable, superseded
- **Superseded**: Replaced by newer ADR (reference new ADR)

## Contributing

When proposing a new ADR:

1. Copy the template from `ADR-000-template.md`
2. Number sequentially
3. Open for discussion
4. Update status based on consensus

---

**Last Updated**: 2026-04-04
