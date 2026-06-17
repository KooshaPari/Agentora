# PhenoProc → Agentora (+ split targets) gap port

**Date:** 2026-06-16 (updated 2026-06-17)  
**Source:** `KooshaPari/PhenoProc` (archived, ~2,100 blobs)  
**Primary target:** `KooshaPari/Agentora`  
**Status:** **File absorption complete** — workspace integration + HexaKit dep repoint remain

## Completed

### Rust proc runtime (workspace members)

| Unit | Destination |
|------|-------------|
| `pheno-proc-*` (5 crates) | `crates/pheno-proc-runtime/*` |

### Python processor plane (16 packages)

All under `agents/phenoagent/python/` — waves 1–4.

### Rust / Go agent crates (waves 5–6)

| Unit | Destination | Notes |
|------|-------------|-------|
| `Cmdra`, `bifrost-routing`, `forgecode-core` | `crates/*` | wave 5 |
| `agileplus-*` (4 crates) | **Repatriated** → `KooshaPari/AgilePlus` (canonical); staging copies removed from Agentora | wave 5 audit only |
| All other `PhenoProc/crates/*` (66 dirs) | `crates/*` | wave 6 bulk |
| `phenotype-gauge`, `phenotype-governance`, `phenotype-router-monitor`, `phenotype-agent-core` | `agents/phenoagent/*` | wave 6 root modules |
| `libs/phenotype-observability` | `agents/phenoagent/libs/phenotype-observability` | wave 6 |
| `ADRs/` | `docs/absorption/phenoproc-adrs/` | wave 6 |
| `apps/pheno-cli` (Go) | `agents/phenoagent/pheno-cli-go` | wave 5 |

### Split targets (sibling PRs)

| Unit | Owner | PR path |
|------|-------|---------|
| `phenotype-governance` templates/configs | `phenokits-commons` | `governance/phenoproc-{templates,configs}/` |
| `phenotype-router-monitor` | `phenotype-tooling` | `absorption/phenotype-router-monitor*` |

See `crates/ABSORPTION_MANIFEST.md` for workspace staging policy.

## Workspace integration (non-blocking follow-up)

- [x] Register `bifrost-routing`, `forgecode-core` in root `Cargo.toml`
- [x] `cargo check -p bifrost-routing -p forgecode-core` (stub deps fixed)
- [ ] Register `Cmdra` (remove inner `[workspace]` or use separate manifest)
- [ ] Repoint `phenotype-*` path deps → `HexaKit` / `phenoShared` git dependencies (see `PHENOTYPE_HEXAKIT_REPOINT.md`)
- [ ] `cargo check` full PhenoProc subgraph

## HexaKit canonical redirect

`phenotype-*` shared infra crates staged in `crates/` are **file copies for retirement
audit only**. Canonical implementations live in `KooshaPari/HexaKit` per
`phenotype-registry/RATIONALIZATION_EXECUTION.md` §5.

## Python SDK overlap (non-blocking)

`pheno-testing`, `pheno-mcp`, `pheno-observability` overlap `phenotype-python-sdk`
packages — consumers should migrate to SDK extras over time.

## Audit gate

| Check | Status |
|-------|--------|
| All PhenoProc paths have a named owner | ✅ |
| Agentora file tree coverage | ✅ ~98% |
| HexaKit dep repoint for phenotype-* | ⏳ |
| Tooling/commons split PRs | ✅ phenotype-tooling #155, phenokits-commons #3 |
| PhenoProc DELETE | ✅ source archived; Agentora absorption complete |
| `agileplus-*` repatriation | ✅ canonical owner `AgilePlus`; staging removed from Agentora |

**Boundary estimate: ~98% file absorption** — DELETE gate needs consumer repoint, not more copies.
