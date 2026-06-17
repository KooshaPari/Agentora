# PhenoProc → Agentora (+ split targets) gap port

**Date:** 2026-06-16 (updated 2026-06-17)  
**Source:** `KooshaPari/PhenoProc` (archived, ~2,100 blobs)  
**Primary target:** `KooshaPari/Agentora`  
**Status:** In progress — Python processor plane complete; Rust/tooling splits outstanding

## Completed (100% of slice)

| PhenoProc boundary unit | Agentora destination | Notes |
|-------------------------|---------------------|-------|
| `crates/pheno-proc-core` | `crates/pheno-proc-runtime/pheno-proc-core` | Byte-identical `lib.rs` |
| `crates/pheno-proc-dedup` | `crates/pheno-proc-runtime/pheno-proc-dedup` | Ported |
| `crates/pheno-proc-queue` | `crates/pheno-proc-runtime/pheno-proc-queue` | Ported |
| `crates/pheno-proc-shm` | `crates/pheno-proc-runtime/pheno-proc-shm` | Ported |
| `crates/pheno-proc-uds` | `crates/pheno-proc-runtime/pheno-proc-uds` | Ported |
| `phenotype-agent-core` (docs) | `agents/phenoagent/phenotype-agent-core/docs` | ADR set present |
| `python/pheno-process` | `agents/phenoagent/python/pheno-process` | Wave 1 (18 files) |
| `python/pheno-llm` | `agents/phenoagent/python/pheno-llm` | Wave 2 (21 files) |
| `python/pheno-clink` | `agents/phenoagent/python/pheno-clink` | Wave 2 (25 files) |
| `python/pheno-workflow` | `agents/phenoagent/python/pheno-workflow` | Wave 3 (53 files) |
| `python/pheno-mcp` | `agents/phenoagent/python/pheno-mcp` | Wave 3 (111 files) |
| `python/pheno-testing` | `agents/phenoagent/python/pheno-testing` | Wave 4 (263 files) |
| `python/pheno-kits` | `agents/phenoagent/python/pheno-kits` | Wave 4 (161 files) |
| `python/pheno-infra` | `agents/phenoagent/python/pheno-infra` | Wave 4 (233 files) |
| `python/pheno-deployment` | `agents/phenoagent/python/pheno-deployment` | Wave 4 (68 files) |
| `python/pheno-cicd` | `agents/phenoagent/python/pheno-cicd` | Wave 4 (13 files) |
| `python/pheno-cli` | `agents/phenoagent/python/pheno-cli` | Wave 4 (77 files) |
| `python/pheno-analytics` | `agents/phenoagent/python/pheno-analytics` | Wave 4 (25 files) |
| `python/pheno-optimization` | `agents/phenoagent/python/pheno-optimization` | Wave 4 (8 files) |
| `python/pheno-providers` | `agents/phenoagent/python/pheno-providers` | Wave 4 (14 files) |
| `python/pheno-quality` | `agents/phenoagent/python/pheno-quality` | Wave 4 (66 files) |
| `python/pheno-observability` | `agents/phenoagent/python/pheno-observability` | Wave 4 (32 files) |
| `crates/Cmdra` | `crates/Cmdra` | Wave 5 (90 files) — workspace TBD |
| `crates/agileplus-*` (4) | `crates/agileplus-*` | Wave 5 (58 files total) |
| `crates/bifrost-routing` | `crates/bifrost-routing` | Wave 5 (4 files) |
| `crates/forgecode-core` | `crates/forgecode-core` | Wave 5 (4 files) |
| `apps/pheno-cli` (Go) | `agents/phenoagent/pheno-cli-go` | Wave 5 — Go edge per LANGUAGE_STACK |

## Outstanding — Agentora / splits

### Rust crates (HexaKit split — do not duplicate long-term)

- Remaining shared `phenotype-*` infra crates in PhenoProc → **HexaKit** (26/44 already there)
- `phenotype-governance`, `phenotype-hub`, `phenotype-infrakit`, `phenotype-mock`, `phenotype-retry`, `phenotype-router-monitor`

### Apps / standalone modules (other targets)

| Unit | Suggested target | Status |
|------|------------------|--------|
| `phenotype-validation` | Agentora validation crate or HexaKit | outstanding |
| `phenotype-gauge` | Agentora metrics integration | outstanding |
| `phenotype-governance` | phenokits-commons/governance | outstanding |
| `phenotype-router-monitor` | phenotype-tooling | outstanding (FocalPoint deferred) |
| `libs/phenotype-observability` | PhenoObservability / python-sdk | outstanding |

### Python long-term redirects (overlap python-sdk)

These are ported under Agentora for boundary closure; thin overlaps with
`phenotype-python-sdk` packages (`testing-kit`, `observability-kit`, `mcp-kit`)
should redirect consumers over time — not block PhenoProc retirement.

## Split — HexaKit

26/44 shared `phenotype-*` Rust infra crates already absorbed into `KooshaPari/HexaKit`.
See `phenotype-registry/RATIONALIZATION_EXECUTION.md` §5.

## Split — phenotype-python-sdk

Processor Python packages that overlap TestingKit/McpKit surfaces should merge into
`packages/*` rather than duplicating under Agentora long-term.

## Merge order (recommended)

1. ~~`pheno-process` + `pheno-llm` + `pheno-clink`~~ ✅
2. ~~`pheno-workflow` + `pheno-mcp`~~ ✅
3. ~~Remaining `python/pheno-*` packages~~ ✅ wave 4
4. ~~AgilePlus / forge crates (`Cmdra`, `agileplus-*`, `forgecode-core`)~~ ✅ wave 5 (files)
5. `apps/pheno-cli` Go → integrate with `agents/phenoagent/pheno-cli-go`
6. Router monitor + governance → tooling repos (blocked: FocalPoint deferred)
7. Register wave-5 crates in workspace + fix `phenotype-*` path deps → HexaKit git deps

## Audit gate

PhenoProc **DELETE** eligibility requires **100%** boundary coverage across
Agentora + HexaKit + phenotype-python-sdk (+ tooling split).

**Current estimate: ~72%** — all Python processor packages + proc runtime + AgilePlus/forge
file copies in Agentora; HexaKit `phenotype-*` dedup + tooling splits remain.
