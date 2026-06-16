# PhenoProc → Agentora (+ split targets) gap port

**Date:** 2026-06-16  
**Source:** `KooshaPari/PhenoProc` (archived, ~2,100 blobs)  
**Primary target:** `KooshaPari/Agentora`  
**Status:** In progress — runtime slice landed; bulk migration outstanding

## Completed (100% of slice)

| PhenoProc boundary unit | Agentora destination | Notes |
|-------------------------|---------------------|-------|
| `crates/pheno-proc-core` | `crates/pheno-proc-runtime/pheno-proc-core` | Byte-identical `lib.rs` |
| `crates/pheno-proc-dedup` | `crates/pheno-proc-runtime/pheno-proc-dedup` | Ported |
| `crates/pheno-proc-queue` | `crates/pheno-proc-runtime/pheno-proc-queue` | Ported |
| `crates/pheno-proc-shm` | `crates/pheno-proc-runtime/pheno-proc-shm` | Ported |
| `crates/pheno-proc-uds` | `crates/pheno-proc-runtime/pheno-proc-uds` | Ported |
| `phenotype-agent-core` (docs) | `agents/phenoagent/phenotype-agent-core/docs` | ADR set present |

## Outstanding — Agentora

### Rust crates (port to `crates/` or `agents/phenoagent/`)

- `Cmdra`, `agileplus-subcmds`, `agileplus-sync`, `agileplus-telemetry`, `agileplus-triage`
- `bifrost-routing`, `forgecode-core`
- `phenotype-governance`, `phenotype-hub`, `phenotype-infrakit`, `phenotype-mock`, `phenotype-retry`, `phenotype-router-monitor`
- Remaining shared `phenotype-*` crates not yet in HexaKit

### Python packages (port to `agents/phenoagent/python/`)

| Package | Role |
|---------|------|
| `pheno-process` | Core process execution |
| `pheno-llm` | LLM integration |
| `pheno-clink` | LLM connectivity |
| `pheno-workflow` | Agent workflow orchestration |
| `pheno-mcp` | MCP tooling |
| `pheno-testing` | Processor-side testing |
| `pheno-kits` | Kit integration |
| `pheno-infra` | Infrastructure helpers |
| `pheno-deployment` | Deploy automation |
| `pheno-cicd` | CI/CD helpers |
| `pheno-cli` | Python CLI surface |
| `pheno-analytics` | Analytics |
| `pheno-optimization` | Optimization |
| `pheno-providers` | Provider adapters |
| `pheno-quality` | Quality gates |
| `pheno-observability` | Observability hooks |

### Apps / standalone modules

| Unit | Suggested target |
|------|------------------|
| `apps/pheno-cli` (Go) | `agents/phenoagent/pheno-cli` (extend beyond docs) |
| `phenotype-validation` | `Agentora` validation crate or `HexaKit` |
| `phenotype-gauge` | `Agentora` metrics integration |
| `phenotype-governance` | `phenokits-commons/governance` |
| `phenotype-router-monitor` | `phenotype-tooling` or dedicated service repo |
| `libs/phenotype-observability` | `HexaKit` / `phenotype-python-sdk` ObservabilityKit |

## Split — HexaKit

26/44 shared `phenotype-*` Rust infra crates already absorbed into `KooshaPari/HexaKit`.
See `phenotype-registry/RATIONALIZATION_EXECUTION.md` §5.

## Split — phenotype-python-sdk

Processor Python packages that overlap TestingKit/McpKit surfaces should merge into
`packages/*` rather than duplicating under Agentora long-term.

## Merge order (recommended)

1. `pheno-process` + `pheno-llm` + `pheno-clink` (core processor boundary)
2. `pheno-workflow` + `pheno-mcp`
3. AgilePlus / forge crates (`Cmdra`, `agileplus-*`, `forgecode-core`)
4. `apps/pheno-cli` Go binary parity
5. Router monitor + governance → tooling repos

## Audit gate

PhenoProc **DELETE** eligibility requires **100%** boundary coverage across
Agentora + HexaKit + phenotype-python-sdk (+ tooling split). Current estimate: **~46%**.
