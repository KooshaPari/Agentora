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

## Phase B (enabled by Accept — not done here)

1. Map `06_SDK_SURFACE_MATRIX.md` ports onto existing `crates/phenotype-port-traits` / agent contracts (forward-only; no LC types in domain).
2. Thin TS/Python façades as **optional** packages; Rust SDK cohabits substrate.
3. Dual-harness + Garden remain consumers via ports — do not reimplement Garden WORM / G1–G7 here.

## Non-goals of this PR

- No façade implementation.
- No LangChain hard-fork import.
- No stock_vs_ours or sharecli work.
