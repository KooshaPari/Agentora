# PhenoProc crate absorption manifest (Agentora staging)

Files under `crates/` from archived `KooshaPari/PhenoProc` (wave 6, 2026-06-17).

## PhenoAgent absorption (P5, 2026-06-19)

Rust agent daemon/skills from `KooshaPari/PhenoAgent` canonical in
`crates/pheno-agent/` (`phenotype-daemon`, `phenotype-skills`). See
[`docs/absorption/PHENOAGENT_ABSORPTION_2026_06_18.md`](../absorption/PHENOAGENT_ABSORPTION_2026_06_18.md).
Source repo deprecated; archive gate P5-2 pending.

## phenoRouterMonitor → phenoAI absorption (P5-4, 2026-06-20)

Rust LLM router from `KooshaPari/phenoRouterMonitor` is canonical in
`KooshaPari/phenoAI/crates/llm-router/` — `LlmProvider` trait, `OpenAiProvider`,
`LlmRouter` with prefix routing + fallback (`lib.rs`, 7 unit tests, `sk-` redaction
pinned). Python `ModelLoader` port + `HuggingFaceLoader` + `LocalLoader` adapters
+ 8 smoke tests live in `KooshaPari/phenoAI/ports/`. Source repo was archived
with only 0-byte placeholders; no code migration. Spec:
[`docs/operations/p5-4-phenoroutermonitor-absorption-2026-06-20.md`](../../../migration-work/registry-wt/docs/operations/p5-4-phenoroutermonitor-absorption-2026-06-20.md).

## Workspace policy

Only `pheno-proc-runtime/*`, `pheno-agent/*`, and root `agentkit` are in the default
`cargo` workspace today. Other ported crates are **staged source** until:

1. `phenotype-*` shared infra → repointed to `HexaKit` git/path deps (canonical)
2. `Cmdra` → registered after inner `[workspace]` refactor
3. `agileplus-*` → **canonical in `KooshaPari/AgilePlus`** (staging copies removed from Agentora 2026-06-17)
3. Agent-specific crates (`cryptora`, `tokn`, …) → trimmed or promoted to workspace members

## Split targets (not duplicated here long-term)

| PhenoProc unit | Canonical owner |
|----------------|-----------------|
| `phenotype-*` infra (30+ crates) | `HexaKit` |
| `phenotype-governance` templates | `phenokits-commons/governance/phenoproc-*` |
| `phenotype-router-monitor` | `phenotype-tooling/absorption/` |
| `libs/phenotype-observability` | `PhenoObservability` / python-sdk |
| Python `pheno-*` | `agents/phenoagent/python/*` (done) |

## Build check (subset)

```bash
cargo check -p bifrost-routing -p forgecode-core  # verified 2026-06-17
```
