# Sidekick → Agentora absorption assessment

**Status:** Blocked — not in rationalization plan; architectural mismatch  
**Plan reference:** `phenotype-registry/RATIONALIZATION_PLAN.md` § Agent Platform  
**Date:** 2026-05-31

## Verdict

| Criterion | Result |
|-----------|--------|
| Listed in RATIONALIZATION_PLAN as Agentora absorbee | **No** — only `PhenoAgent` stub and `PhenoProc` runtime |
| Agentora role | Rust **agent framework** (agentkit): skills, tools, memory, hexagonal layers |
| Sidekick role | **Agent utility collection**: MCP presence, cheap-LLM routing, messaging stubs |
| Workspace overlap | None — different crate graphs and consumers |
| Sidekick `phenotype-errors` path dep | `path = "../pheno/crates/phenotype-errors"` — **orphan** unless `pheno` sibling exists |
| Subtree merge feasibility | **Poor** — would nest unrelated MCP utilities inside framework repo; breaks Sidekick FR/test layout |

## Agent platform canonical shape (per plan)

| Repo | Keep / absorb |
|------|----------------|
| **Agentora** | PhenoAgent stub → `crates/pheno-agent/*`; PhenoProc runtime → `crates/pheno-proc-runtime/*` (already present in workspace) |
| **thegent** | Keep — Python dispatcher, separate language target |
| **phenoAI** | Absorbs phenoRouterMonitor core + monitoring UI |
| **Sidekick** | **Not listed** — remains standalone collection |

## Why absorption is deferred

1. **Governance:** Forcing Sidekick into Agentora exceeds the documented agent-platform scope; risks conflating *framework* with *MCP micro-utilities*.
2. **Dependency graph:** Sidekick expects `../pheno/` on disk; Agentora is self-contained. Absorption requires HexaKit/pheno path migration (Step 7 sign-off territory).
3. **Collection model:** Sidekick README defines 3 canonical members with independent FR coverage; Agentora targets framework adopters, not MCP tool hosts.

## Recommended path

1. **Keep Sidekick standalone** until `phenotype-errors` path is repointed to HexaKit/git dep (post–pheno→HexaKit merge).
2. **Integration boundary:** Agentora agents *consume* Sidekick MCP servers via protocol, not monorepo nesting.
3. Revisit only if `phenotype-registry` agent-platform table is explicitly amended to absorb Sidekick.

## Build verification (absorber)

```powershell
$env:CARGO_TARGET_DIR = 'E:\cargo-target\Agentora'
cargo check --workspace
```
