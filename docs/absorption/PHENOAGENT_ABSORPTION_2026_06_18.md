# PhenoAgent → Agentora (P5, ECOSYSTEM_MAP §6)

| Field | Value |
|-------|-------|
| **Source repo** | https://github.com/KooshaPari/PhenoAgent |
| **Absorption date** | 2026-06-18 |
| **Registry wave** | P5 (ECOSYSTEM_MAP §6 / Cluster B — Agent Runtimes) |
| **Disposition** | ABSORB |
| **Canonical owner** | **Agentora** (this repo) — `crates/pheno-agent/` is the canonical Rust implementation; `PhenoAgent` repo is the historical governance/PRD surface |
| **ECOSYSTEM_MAP row** | §6 *Retirements / Merges* → "Merge PhenoAgent stub → Agentora" |
| **Adjacent row** | §3 Cluster B verdict: "PhenoAgent — Stub (empty manifest); Merge stub into Agentora; retire repo" |

## Summary

`PhenoAgent` held the historical agent orchestration, daemon, and CLI scaffolds
(`phenotype-daemon/`, `pheno-cli/`, `phenotype-agent-core/`, `agentapi/`,
`CLIProxyAPI/`) plus the PRD/ADR/FR/governance set. The canonical implementation
lives in this repo under `crates/pheno-agent/`, integrated via the PhenoProc
absorption gap port (see `PHENOPROC_GAP_PORT.md`) and the W18b repoint pass
(see `PHENOTYPE_HEXAKIT_REPOINT.md`).

Per the registry P5 action, `PhenoAgent` is the deprecation pointer; new work
on the agent framework belongs in this repo.

## Mapping (PhenoAgent → Agentora)

| PhenoAgent path | Role | Canonical surface in Agentora |
|-----------------|------|-------------------------------|
| `phenotype-agent-core/` | Rust core traits and types | `crates/pheno-agent/` (core module) |
| `phenotype-daemon/` | Agent orchestration daemon | `crates/pheno-agent/` (daemon/ module) + `crates/pheno-proc-runtime/` |
| `pheno-cli/` | CLI surface (docs/adrs preserved) | `crates/pheno-agent/` (cli/ module) + `agents/phenoagent/pheno-cli-go/` |
| `agentapi/` | gRPC API definitions | `crates/pheno-agent/` (api/ module) |
| `CLIProxyAPI/` | Go CLI proxy plane | `cliproxyapi-plusplus` (Wave G16, peer gateway) |
| `docs/adr/*.md` | Architecture Decision Records | `docs/absorption/phenoproc-adrs/` (subset) + `crates/pheno-agent/docs/` |
| `docs/specs/FR.md` | Functional-requirements tracker | `crates/pheno-agent/FUNCTIONAL_REQUIREMENTS.md` |
| `docs/boundary/PhenoAgent.md` | Boundary description | `docs/boundary/` in this repo |
| `docs/intent/PhenoAgent.md` | Intent document | `docs/intent/` in this repo |
| `PRD.md`, `PLAN.md`, `CHARTER.md` | Product/plan/charter | `crates/pheno-agent/{PRD,PLAN,CHARTER}.md` |
| `AGENTS.md`, `CLAUDE.md` | Agent governance | Root `AGENTS.md` / `CLAUDE.md` |
| `worklog.md`, `worklogs/` | Work audit | `crates/pheno-agent/worklog.md` |

## Direction note

The PhenoAgent repo received a forward port from `Agentora/crates/pheno-agent/C`
in commit `aee873f` ("chore(deps): port Agentora/crates/pheno-agent/C forward
into PhenoAgent (#56)"). That port is now reversed by this absorption record:
the canonical home is `Agentora`, and `PhenoAgent` carries a deprecation
pointer to this repo.

## Registry reference

- `phenotype-registry/ECOSYSTEM_MAP.md` §6 P5 row.
- `phenotype-registry/ECOSYSTEM_MAP.md` §3 Cluster B verdict.
- PhenoProc gap port: `docs/absorption/PHENOPROC_GAP_PORT.md`.
- W18b repoint plan: `docs/absorption/PHENOTYPE_HEXAKIT_REPOINT.md`.

## Do not

- Open new feature work against the archived `PhenoAgent` repo.
- Treat `PhenoAgent` as the canonical agent implementation — use
  `Agentora/crates/pheno-agent/` instead.
- Fork `PhenoAgent` for ongoing development; the repo is the historical
  governance/PRD surface only.
