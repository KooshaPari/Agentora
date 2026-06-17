# Architectural Decision Records

This directory contains Architectural Decision Records (ADRs) for the Phenotype Router Monitor project. ADRs capture significant architectural decisions, their context, and consequences to provide a historical record and guide future maintainers.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. An ADR is a short text file that describes:

- The decision being made
- The context and forces driving the decision
- The decision itself
- The consequences of that decision

## Format

Each ADR follows this structure:

1. **Title:** ADR-NNN: Short descriptive title
2. **Status:** Proposed, Accepted, Deprecated, Superseded
3. **Date:** When the decision was made
4. **Context:** The problem we're solving and forces at play
5. **Decision:** What we're doing
6. **Consequences:** What this means (positive, negative, mitigations)
7. **References:** Related documents and research

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-async-runtime.md) | Async Runtime Architecture | Accepted | 2026-04-04 |
| [002](002-metrics-export.md) | Metrics Export Strategy | Accepted | 2026-04-04 |
| [003](003-health-check-pattern.md) | Health Check Pattern | Accepted | 2026-04-04 |

## Status Definitions

- **Proposed:** Under discussion, not yet accepted
- **Accepted:** Decision approved and being implemented
- **Deprecated:** Decision no longer applicable, but not yet replaced
- **Superseded:** Replaced by a newer ADR (link to replacement)

## Contributing

When proposing a new ADR:

1. Create a new file with the next sequential number
2. Start with status "Proposed"
3. Submit for review via PR
4. After approval, change status to "Accepted"
5. Update this index

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Documenting Architecture Decisions](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions) by Michael Nygard
- [OpenTelemetry ADR Process](https://github.com/open-telemetry/opentelemetry-rust/tree/main/docs/adr)
