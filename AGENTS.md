# AGENTS.md — Agentora (`agentkit` crate)

Rust hexagonal-architecture framework for AI agents — skill system, tool registry, two-tier memory, and serializable lifecycle events.

## Repository identity

- Language: Rust (edition 2021, see `rust-toolchain.toml`).
- Crate name: `agentkit` (verified in `Cargo.toml`).
- Version: `0.1.0`.
- License: `MIT OR Apache-2.0`.
- Entry point: `Cargo.toml` (root); source under `src/`.
- Architecture: 4-layer hexagonal (Domain / Application / Adapters / Infrastructure).

## Feature flags (verified from README)

| Feature | Description | Pulls in |
|---------|-------------|----------|
| `openai` | OpenAI API support | `reqwest 0.11` |
| `redis-memory` | Redis memory backend | `redis 0.23` |
| `sqlite-memory` | SQLite memory backend | `rusqlite 0.29` |

## Build & test

```bash
cargo build
cargo test
cargo clippy -- -D warnings

# With features
cargo test --features "openai sqlite-memory"
```

## Governance

- Standards: `STANDARDS.md`.
- API contract audit: `API_CONTRACT_AUDIT.md`.
- Changelog: `CHANGELOG.md`.
- Docs: `docs/`.

## Commit & branch convention

- Conventional Commits.
- Branch: `<type>/<topic>`.

## Agent guardrails

- Preserve hexagonal-layer boundaries: domain code MUST NOT import adapters or infrastructure.
- New backends go behind feature flags — do not pull heavy runtime deps into the default build.
- The repository slug is `Agentora` but the crate name is `agentkit`. Do not rename the crate without coordinated release planning.
