# Agentora ↔ Phenotype SDK / ADR alignment

**Date:** 2026-07-22  
**ADR:** Phenotype session `20260722-harness-agentora-restored-forks` — **Accepted Option C (hybrid façade)**  
**This repo:** `KooshaPari/Agentora` (existing substrate / agentkit workspace)

## Pointers (canonical specs live in Phenotype docs shelf)

| Doc | Path (on Phenotype machine) |
|-----|-----------------------------|
| Charter #76 | `Phenotype/repos/docs/sessions/20260722-harness-agentora-restored-forks/AGENTORA_CHARTER.md` |
| ADR #78 Accepted | `.../ADR-20260722-agentora-fork-vs-rewrite.md` |
| SDK contracts #79 | `.../06_SDK_SURFACE_MATRIX.md` |
| Micro dogfood #77 | `.../07_MICRO_DOGFOOD.md` + `artifacts/micro-dogfood-harness-plane-20260722.json` |

## Phase B (landed in `phenotype-agent-contracts`)

1. **Done:** Map `06_SDK_SURFACE_MATRIX.md` ports into `rust/phenotype-agent-contracts`:
   - `sdk_dto` — wire DTOs (`AgentMessage`, `ModelRequest`, `EvalHookRef`, …)
   - `sdk_ports` — hexagonal traits (`ModelPort`, `ToolPort`, `SessionMemoryPort`, `SchedulerQueuePort`, `ObservabilityPort`, `EvalGardenPort`)
   - `sdk_bridges` — legacy `LLM` / `ToolExecutor` / `MemoryPort` adapters
   - `sdk_runtime` — in-memory scheduler + recording garden + fail-loud unconfigured observability
2. Thin TS/Python façades remain **optional** follow-ups; Rust SDK cohabits substrate.
3. Dual-harness + Garden remain consumers via ports — do not reimplement Garden WORM / G1–G7 here.

## Non-goals (still)

- No LangChain hard-fork import into domain crates.
- No stock_vs_ours or sharecli work.
- Peer-SDK-embedded bake-off stays Phase B deferred (charter).
