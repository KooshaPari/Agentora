# Phenotype-* staging → canonical dep repoint plan

**Owner:** Agentora (staging only)  
**Canonical:** `KooshaPari/HexaKit` (infra) + `KooshaPari/phenoShared` (shared cross-cutting)  
**Authority:** `phenotype-registry/BOUNDARY_OWNERS.md`, ADR-ECO-006

## Policy

Staged `crates/phenotype-*` under Agentora are **audit copies** from PhenoProc absorption (#79).
They must not remain as path-deps long-term. Consumers should use:

```toml
phenotype-error-core = { git = "https://github.com/KooshaPari/phenoShared", branch = "main" }
# or specific HexaKit crate git dep when not yet in phenoShared
```

## Repoint waves

| Wave | Crates | Target | Status |
|------|--------|--------|--------|
| 1 | Leaf crates (no Agentora path consumers) | phenoShared git | ✅ `phenotype-errors`, `phenotype-error-macros`, `phenotype-config-loader` (2026-06-17) |
| 2 | `bifrost-routing`, `forgecode-core` workspace members | verify no phenotype-* path deps | ✅ workspace registered |
| 3 | Remaining `crates/phenotype-*` (~30) | HexaKit git per crate name | ⏳ |
| NB | `Cmdra` inner `[workspace]` | flatten or exclude | ⏳ deferred |

## Wave 1 (2026-06-17)

Leaf staging crates repointed to `phenoShared` git (no Agentora path consumers):

| Crate | Repointed dep |
|-------|----------------|
| `phenotype-errors` | `phenotype-error-core` |
| `phenotype-error-macros` | `phenotype-error-core` |
| `phenotype-config-loader` | `phenotype-config-core` |

Remaining `path = "../phenotype-*"` in `crates/` (e.g. `phenotype-validation` → `phenotype-test-fixtures` dev-dep) deferred to wave 3 / HexaKit.

## Verification

```bash
rg 'path = "\.\./phenotype-' crates/ --glob Cargo.toml
cargo check -p bifrost-routing -p forgecode-core
```

## Non-goals

- Duplicating HexaKit crates into Agentora workspace members
- Repatriating agileplus (done → AgilePlus #81)
