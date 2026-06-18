# Phenotype-* staging → canonical dep repoint plan

**Owner:** Agentora (staging only)  
**Canonical:** `KooshaPari/HexaKit` (infra) + role-owner terminals (`phenotype-types`, `phenotype-config`, …)  
**Authority:** `phenotype-registry/BOUNDARY_OWNERS.md`, ADR-ECO-006, ADR-ECO-014

## Policy

Staged `crates/phenotype-*` under Agentora are **audit copies** from PhenoProc absorption (#79).
They must not remain as path-deps long-term. Consumers should use:

```toml
phenotype-error-core = { git = "https://github.com/KooshaPari/phenotype-types", branch = "main" }
phenotype-config-loader = { git = "https://github.com/KooshaPari/phenotype-config", branch = "main" }
# or specific HexaKit crate git dep when not yet in a terminal owner
```

## Repoint waves

| Wave | Crates | Target | Status |
|------|--------|--------|--------|
| 1 | Leaf crates (no Agentora path consumers) | role-owner git (W18b) | ✅ `phenotype-errors`, `phenotype-error-macros`, `phenotype-config-loader` (2026-06-18) |
| 2 | `bifrost-routing`, `forgecode-core` workspace members | verify no phenotype-* path deps | ✅ workspace registered |
| 3 | Remaining `crates/phenotype-*` (~28) | HexaKit / phenoShared / tooling git per `MIGRATED.md` | ✅ stubs 2026-06-17 |
| NB | `Cmdra` inner `[workspace]` | flatten or exclude | ⏳ deferred |

## Wave 1 (2026-06-18, W18b)

Leaf staging crates repointed to role-owner terminals (H14 complete):

| Crate | Repointed dep / owner |
|-------|------------------------|
| `phenotype-errors` | `phenotype-error-core` → `phenotype-types` |
| `phenotype-error-macros` | `phenotype-error-core` → `phenotype-types` |
| `phenotype-config-loader` | self-contained stub → `phenotype-config` (no `phenotype-config-core` dep) |

Remaining `path = "../phenotype-*"` in `crates/` (e.g. `phenotype-validation` → `phenotype-test-fixtures` dev-dep) deferred to wave 3 / HexaKit.

## Verification

```bash
rg 'path = "\.\./phenotype-' crates/ --glob Cargo.toml
cargo check -p bifrost-routing -p forgecode-core
```

## Non-goals

- Duplicating HexaKit crates into Agentora workspace members
- Repatriating agileplus (done → AgilePlus #81)
