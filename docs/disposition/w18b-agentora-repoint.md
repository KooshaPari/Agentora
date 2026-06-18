# W18b — Agentora phenoShared stub repoint

**Date:** 2026-06-18  
**Wave:** W18b-G (pheno fleet repoint)  
**Owner:** Agentora (staging audit copies only)  
**Status:** **COMPLETE** — H14 merged; stubs repointed to role-owner terminals

## Summary

Three legacy stub crates under `crates/` repointed from interim `phenoShared` git pins to role-owner terminals per [GATEWAY_MERGE_DAG W18b-G](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/GATEWAY_MERGE_DAG.md).

## H14 readiness (2026-06-18)

| Terminal repo | Required crate | Present? | Evidence |
|---------------|----------------|----------|----------|
| `KooshaPari/phenotype-types` | `phenotype-error-core` | **Yes** | [phenotype-types#1](https://github.com/KooshaPari/phenotype-types/pull/1) merged |
| `KooshaPari/phenotype-config` | `phenotype-config-loader` | **Yes** | [phenotype-config#2](https://github.com/KooshaPari/phenotype-config/pull/2) merged |
| `KooshaPari/HexaKit` | H14 decompose repoint | **Yes** | [HexaKit#267](https://github.com/KooshaPari/HexaKit/pull/267) merged |

> **Note:** `phenotype-config-core` was not absorbed into `phenotype-config`; the loader stub is self-contained and no longer pins `phenotype-config-core`.

## Applied repoint

Branch: `feat/w18b-phenoshared-repoint`

### `crates/phenotype-errors/Cargo.toml`

| Line | Before | After |
|------|--------|-------|
| repository | `phenoShared` | `phenotype-types` |
| `phenotype-error-core` git dep | `phenoShared` | `phenotype-types` |

### `crates/phenotype-error-macros/Cargo.toml`

| Line | Before | After |
|------|--------|-------|
| repository | `phenoShared` | `phenotype-types` |
| `phenotype-error-core` git dep | `phenoShared` | `phenotype-types` |

### `crates/phenotype-config-loader/Cargo.toml`

| Line | Before | After |
|------|--------|-------|
| repository | `phenoShared` | `phenotype-config` |
| `phenotype-config-core` git dep | `phenoShared` | **removed** (unused; terminal loader is self-contained) |

## Verification

```bash
cargo check --manifest-path crates/phenotype-errors/Cargo.toml
cargo check --manifest-path crates/phenotype-error-macros/Cargo.toml
cargo check --manifest-path crates/phenotype-config-loader/Cargo.toml
```

## Non-goals

- Modifying `phenotype-types`, `phenotype-config`, `HexaKit`, or registry G18/G19 work
- Repointing remaining `crates/phenotype-*` (see [PHENOTYPE_HEXAKIT_REPOINT.md](../absorption/PHENOTYPE_HEXAKIT_REPOINT.md))

## Related

- [PHENOTYPE_HEXAKIT_REPOINT.md](../absorption/PHENOTYPE_HEXAKIT_REPOINT.md) — wave-1 role-owner repoint
- [GATEWAY_MERGE_DAG W18b-G](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/GATEWAY_MERGE_DAG.md)
- Supersedes draft [PR #88](https://github.com/KooshaPari/Agentora/pull/88) (blocked disposition plan)
