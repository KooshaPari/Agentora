# ORIGIN — Agentora provenance

**Date:** 2026-06-18
**Status:** Active (this file documents the canonical source-of-truth for the Agentora codebase)
**Author:** Forge subagent (L5-110) — McpKit absorption audit
**Supersedes:** N/A — first origin record

---

## Source repositories

This `KooshaPari/Agentora` repo (package: `agentkit`) is the canonical,
authoritative source for the Rust hexagonal agent framework. It is the
single source of truth and the only location where active development
occurs. Any third-party copy must be reconciled against `main` here.

### Primary canonical location

- **GitHub:** `KooshaPari/Agentora` (case-insensitive; `KooshaPari/agentora` resolves identically)
- **Description:** _Rust hexagonal-architecture framework for AI agents — skill system, tool registry, two-tier memory (ring + persistent), and serializable lifecycle events_
- **License:** Apache-2.0
- **Local clone:** `/Users/kooshapari/CodeProjects/Phenotype/repos/agentora/`

### Previously-nested copies (now retired)

| Source                                      | Status                               | Resolution                                                                                                                             |
| :------------------------------------------ | :----------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `KooshaPari/McpKit/rust/agentora/` (nested) | RETIRED — McpKit archived 2026-06-17 | Was a stale v0.1.0 snapshot (13 commits, 2026-03-25 → 2026-04-25). All content subsumed by canonical repo. See § "Absorption history". |
| `KooshaPari/McpKit/rust/agentora/.git/`     | RETIRED                              | Nested git history superseded by canonical repo (147 commits at time of absorption).                                                   |

---

## Why this file exists

During the McpKit absorption audit (L5-110, 2026-06-18), the McpKit repo
was archived on GitHub and its contents frozen. The nested `rust/agentora/`
sub-repo was an early, partial snapshot of the agentkit framework that had
since been developed independently under `KooshaPari/Agentora`. Without an
explicit origin record, future readers risk:

1. **Confusion** — `McpKit/rust/agentora/` looks like the agent framework
   "source" but is actually a stale snapshot.
2. **Drift** — A future agent might attempt to "fix" the McpKit nested copy
   instead of working on the canonical repo.
3. **Loss** — A future McpKit cleanup might delete the nested copy,
   discarding git history that is no longer present in canonical main.

This file declares: **`KooshaPari/Agentora` is the canonical source.**
Any reference to "the agentkit repo" or "the agentora repo" resolves here.

---

## Absorption history

### L5-110 — McpKit absorption audit (2026-06-18)

**Trigger:** User directive (per AGENTS.md `STALE / warnings` §):
_"merge all over to kooshapari → then reconcile/absorb to proper repos.
e.g. dispatch-mcp should be deleted as it needs to have all remaining
work fully absorbed to substrate"_ — applied generally to MCP and
non-MCP nested sub-repos in McpKit.

**Scope:** `KooshaPari/McpKit/rust/agentora/` (13 commits, 26 files,
~1,200 LoC scaffold).

**Audit classification (per McpKit absorption rubric):**

| Dimension          | Verdict                                                                                                             |
| :----------------- | :------------------------------------------------------------------------------------------------------------------ |
| Domain fit         | **NO_MERIT (for MCP)** — agent framework, not MCP server. Out-of-domain for McpKit's MCP absorption.                |
| Lifecycle risk     | **MEDIUM** — has its own `.git/`, `Cargo.toml`, `README.md`, `.github/workflows/`. Not a transient file.            |
| Reuse value        | **MEDIUM** — hexagonal scaffold, but only ~1,200 LoC, low test coverage (~1%).                                      |
| Content overlap    | **100% subsumed** — all 26 files exist in canonical `KooshaPari/Agentora` and the canonical is newer (147 commits). |
| Recommended action | **Document and retain canonical-only** — do not migrate; the canonical is already authoritative.                    |

**Decision:** No migration. The canonical `KooshaPari/Agentora` already
contains all McpKit sub-repo content with strictly newer revisions (thiserror
2.0 vs 1.0; reqwest 0.13 vs 0.12; full 47-crate workspace; 9 integration
test files vs 0; 9 CI workflows vs 2; 2085 files vs 26). Copying the
nested snapshot on top of canonical would be **destructive** (downgrading
content). Action taken: this ORIGIN.md, plus a PR to canonical main
documenting the provenance.

**Files inspected in McpKit sub-repo (read-only, no modifications):**

- `README.md` — 554 lines (v0.1.0 doc, older version of canonical README)
- `Cargo.toml` — 55 lines (thiserror 1.0, reqwest 0.12, redis 0.27)
- `CHANGELOG.md` — 11 lines (only entry: 0.1.0 / 2026-03-25)
- `STANDARDS.md` — 46 lines (xDD methodologies)
- `API_CONTRACT_AUDIT.md` — 106 lines (audit of 18 types: 6 with serde, 12 missing)
- `.github/workflows/ci.yml` — 61 lines (build, clippy, test, fmt jobs)
- `.github/workflows/pages-deploy.yml` — 61 lines (GitHub Pages)
- `src/lib.rs` — 25 lines (prelude + re-exports)
- `src/bin/main.rs` — 5 lines (placeholder `println!`)
- `src/domain/{agents,skills,tools,memory,context,ports,events,errors}/mod.rs` — full domain
- `src/application/mod.rs` — 70 lines (`AgentExecutor`, `SimpleAgent`)
- `src/adapters/{llm,memory}/mod.rs` — 1 line stubs (placeholders)
- `src/infrastructure/{mod.rs,error.rs}` — error re-exports
- `docs/PATH_TO_SIDEKICK.md` — 110 lines (Sidekick qualification roadmap)
- `.gitignore` — 26 lines (Cargo standard)

All 26 files have a superseding counterpart in canonical `KooshaPari/Agentora`.

**Files added to canonical (this PR):** this ORIGIN.md only.

---

## Active canonical locations

| What                             | Where                                                                                                                                       |
| :------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| Crate source (agentkit v0.1.0)   | `src/` at repo root                                                                                                                         |
| Crate source (47 staged members) | `crates/` (phenotype-\*, bifrost-routing, forgecode-core, etc.)                                                                             |
| Integration tests                | `tests/` (9 files)                                                                                                                          |
| Documentation                    | `docs/` (12 files)                                                                                                                          |
| CI                               | `.github/workflows/` (9 workflows: ci, audit, cargo-deny, governance, pages-deploy, release-attestation, scorecard, sonarcloud, trufflehog) |
| Cargo workspace                  | Root `Cargo.toml` (47 members + 2 excluded for name collision)                                                                              |
| Governance                       | `AGENTS.md`, `CLAUDE.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, `FUNDING.yml`                               |

---

## Name reconciliation

This repo is named `Agentora` on GitHub but the Rust package name is
`agentkit`. Both refer to the same codebase. The naming split is historical:

- **`agentkit`** — Rust crate name (Cargo convention: kebab-case, no
  underscores). Used in `Cargo.toml [package] name = "agentkit"`. Used in
  README examples. Used in import statements: `use agentkit::prelude::*;`.
- **`Agentora`** — GitHub repo name (was rebranded from `agentkit` to
  `Agentora` around 2026-06 to disambiguate from the unrelated npm
  `agentkit` package and align with the broader Phenotype org naming).

**For consumers:** depend on the crate as `agentkit`; reference the repo
as `KooshaPari/Agentora`.

---

## Provenance of crates staged under `crates/`

The 47 `crates/*` members of this workspace are staged absorption targets
from across the Phenotype fleet. Each member carries its own git history
in its own upstream repo (see `crates/ABSORPTION_MANIFEST.md` for the
manifest). The members are NOT yet inlined here; they remain as path
dependencies or git stubs pending wave-based inlining per ADR-022 and
ADR-035 (see `docs/adr/2026-06-15/` and `docs/adr/2026-06-18/`).

---

## See also

- `AGENTS.md` — repo-local AGENTS guide (work-state, conventions, build commands)
- `CLAUDE.md` — Claude-specific guidance
- `docs/boundary/Agentora.md` — boundary declaration (what this repo IS and IS NOT)
- `docs/intent/Agentora.md` — intent statement
- `docs/rationalization/sidekick-absorption.md` — Sidekick absorption history
- `docs/absorption/PHENOTYPE_HEXAKIT_REPOINT.md` — HexaKit repoint wave plan
- `docs/absorption/PHENOPROC_GAP_PORT.md` — PhenoProc gap-port plan
- `docs/specs/FR.md` — functional requirements
- `docs/specs/TRACEABILITY.md` — requirements ↔ tests traceability
- `API_CONTRACT_AUDIT.md` — public API serialization schema audit (18 types)
- `STANDARDS.md` — development standards (xDD methodologies, SOLID, code quality gates)
- `docs/PATH_TO_SIDEKICK.md` — Sidekick qualification roadmap
- `crates/ABSORPTION_MANIFEST.md` — staged-crate absorption manifest

---

**L5-110 audit complete.** No content loss. No destructive migration.
Canonical repo (`KooshaPari/Agentora`) verified at commit `031e40b feat(domain): add MCP ports and integration documentation (#87)`.
