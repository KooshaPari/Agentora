# W18b — Agentora phenoShared stub repoint (BLOCKED)

**Date:** 2026-06-18  
**Wave:** W18b-G (pheno fleet repoint)  
**Owner:** Agentora (staging audit copies only)  
**Status:** **BLOCKED** — do **not** merge until terminal owners publish `phenotype-error-core` / `phenotype-config-core`

## Summary

Three legacy stub crates under `crates/` still pin `phenoShared` git for their core deps (wave-1 interim, [#83](https://github.com/KooshaPari/Agentora/pull/83)). W18b repoints them to role-owner terminals per [GATEWAY_MERGE_DAG W18b-G](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/GATEWAY_MERGE_DAG.md).

## Readiness check (2026-06-18)

| Terminal repo | Required crate | Present? | Evidence |
|---------------|----------------|----------|----------|
| `KooshaPari/phenotype-types` | `phenotype-error-core` | **No** | Repo is Python-only (`pyproject.toml`, `src/pheno_types/`); no `crates/` workspace |
| `KooshaPari/phenotype-config` | `phenotype-config-core` | **No** | Repo deprecated (ADR-031); only `crates/settly/` remains; no `phenotype-config-core` |

Current canonical sources still live in `KooshaPari/phenoShared`:

- `phenoShared/crates/phenotype-error-core/`
- `phenoShared/crates/phenotype-config-core/`

## Blocked on

| Lane | Owner | Link | Gate |
|------|-------|------|------|
| H14 | HexaKit | Branch [`feat/wave14-phenoshared-decompose`](https://github.com/KooshaPari/HexaKit/tree/feat/wave14-phenoshared-decompose) (no PR yet) | phenoShared decompose → DOMAIN_ROLES owners (ADR-ECO-014) |
| H14 absorption | phenotype-types | *(pending)* | Publish `crates/phenotype-error-core/` Rust workspace member |
| H14 absorption | phenotype-config | *(pending)* | Publish `crates/phenotype-config-core/` (or confirm Configra redirect per ADR-031) |

Registry ledger: [wave15-execution § W18b](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/operations/wave15-execution-2026-06-17.md).

## Planned repoint (apply when unblocked)

Branch: `feat/w18b-phenoshared-repoint`

### `crates/phenotype-errors/Cargo.toml`

| Line | Current | Target |
|------|---------|--------|
| 7 | `repository = "https://github.com/KooshaPari/phenoShared"` | `repository = "https://github.com/KooshaPari/phenotype-types"` |
| 10 | `phenotype-error-core = { git = "https://github.com/KooshaPari/phenoShared", branch = "main" }` | `phenotype-error-core = { git = "https://github.com/KooshaPari/phenotype-types", branch = "main" }` |

### `crates/phenotype-error-macros/Cargo.toml`

| Line | Current | Target |
|------|---------|--------|
| 8 | `repository = "https://github.com/KooshaPari/phenoShared"` | `repository = "https://github.com/KooshaPari/phenotype-types"` |
| 16 | `phenotype-error-core = { git = "https://github.com/KooshaPari/phenoShared", branch = "main" }` | `phenotype-error-core = { git = "https://github.com/KooshaPari/phenotype-types", branch = "main" }` |

### `crates/phenotype-config-loader/Cargo.toml`

| Line | Current | Target |
|------|---------|--------|
| 8 | `repository = "https://github.com/KooshaPari/phenoShared"` | `repository = "https://github.com/KooshaPari/phenotype-config"` |
| 11 | `phenotype-config-core = { git = "https://github.com/KooshaPari/phenoShared", branch = "main" }` | `phenotype-config-core = { git = "https://github.com/KooshaPari/phenotype-config", branch = "main" }` |

> **Note:** `phenotype-config` is deprecated per ADR-031; if H14 lands `phenotype-config-core` in `Configra` instead, update line 8/11 to `KooshaPari/Configra` before merge.

## Merge gate

1. `phenotype-types` publishes `phenotype-error-core` on `main` (git dep resolves).
2. Terminal owner publishes `phenotype-config-core` on agreed repo (`phenotype-config` or `Configra`).
3. H14 decompose PR merged; phenoShared terminal owners sign off.
4. `cargo check -p phenotype-errors -p phenotype-error-macros -p phenotype-config-loader` passes in Agentora.

## Non-goals

- Modifying `phenotype-types`, `phenotype-config`, `HexaKit`, or registry G18/G19/H14 work
- Merging this PR before terminal owners are ready
- Repointing remaining `crates/phenotype-*` (see [PHENOTYPE_HEXAKIT_REPOINT.md](../absorption/PHENOTYPE_HEXAKIT_REPOINT.md))

## Related

- [PHENOTYPE_HEXAKIT_REPOINT.md](../absorption/PHENOTYPE_HEXAKIT_REPOINT.md) — wave-1 interim phenoShared pins
- [GATEWAY_MERGE_DAG W18b-G](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/GATEWAY_MERGE_DAG.md)
