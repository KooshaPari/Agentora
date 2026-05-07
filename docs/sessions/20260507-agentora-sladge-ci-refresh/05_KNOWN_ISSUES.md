# Known Issues

## Deferred Integration

Canonical Agentora has unrelated untracked `ARCHITECTURE.md`, so this refresh
remains isolated.

## Formatting Drift

`cargo fmt --check` still reports pre-existing Rust formatting drift in
`src/application/mod.rs`, `src/domain/agents/mod.rs`,
`src/domain/memory/mod.rs`, `src/domain/mod.rs`, `src/domain/ports/mod.rs`,
`src/domain/skills/mod.rs`, `src/domain/tools/mod.rs`, and `src/lib.rs`.
Those files were outside this README/session-doc refresh.

## Superseded Branch

The older `docs/agentora-sladge-current` branch at `78551ec` diverged from
current `ci/pin-trufflehog` and should be treated as stale evidence after this
refresh.
