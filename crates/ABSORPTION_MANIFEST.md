# PhenoProc crate absorption manifest (Agentora staging)

Files under `crates/` from archived `KooshaPari/PhenoProc` (wave 6, 2026-06-17).

## Workspace policy

Only `pheno-proc-runtime/*`, `pheno-agent/*`, and root `agentkit` are in the default
`cargo` workspace today. Other ported crates are **staged source** until:

1. `phenotype-*` shared infra → repointed to `HexaKit` git/path deps (canonical)
2. `Cmdra` / `agileplus-*` → registered after missing workspace siblings land
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
