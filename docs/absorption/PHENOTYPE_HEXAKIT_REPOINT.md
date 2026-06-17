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
| 1 | Leaf crates (no Agentora path consumers) | phenoShared git | ⏳ |
| 2 | `bifrost-routing`, `forgecode-core` workspace members | verify no phenotype-* path deps | ✅ workspace registered |
| 3 | Remaining `crates/phenotype-*` (~30) | HexaKit git per crate name | ⏳ |
| NB | `Cmdra` inner `[workspace]` | flatten or exclude | ⏳ deferred |

## Verification

```bash
rg 'path = "\.\./phenotype-' crates/ --glob Cargo.toml
cargo check -p bifrost-routing -p forgecode-core
```

## Non-goals

- Duplicating HexaKit crates into Agentora workspace members
- Repatriating agileplus (done → AgilePlus #81)
