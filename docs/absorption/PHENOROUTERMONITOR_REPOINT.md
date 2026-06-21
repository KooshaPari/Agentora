# phenoRouterMonitor → phenoAI Absorption

> Absorption record for the `phenoRouterMonitor` capability into
> `phenoAI`. Completes the Phase 5 agent-runtime absorption sweep
> alongside the prior `phenoAgent`, `phenoProc`, and `phenoHexaKit`
> repoints. No code moves; this is a capability repointing under the
> `phenoAI` umbrella so consumers and downstream registries track a
> single source of truth.

## Repoint summary

| Field              | Value                                                          |
|--------------------|----------------------------------------------------------------|
| Source crate       | `phenoRouterMonitor` (monitoring + routing telemetry)           |
| Target crate       | `phenoAI` (Phase 5 unified agent runtime)                      |
| Source path        | `crates/thegent-router-monitor/`                               |
| Target path        | `crates/phenoai/src/router_monitor/`                           |
| Capability kind    | Monitoring + routing telemetry (read-only by default)          |
| Repoint type       | Capability repoint (no symbol deletion in target)              |
| Consumers updated  | `thegent`, `phenotype-registry`, `phenotype-otel`               |
| Manifest row       | `crates/ABSORPTION_MANIFEST.md` (entry added 2026-06-21)       |
| Traceability rows  | `docs/specs/TRACEABILITY.md` (FR-LLM-001..004)                 |
| Status             | **DONE** (paperwork-only)                                      |
| Date               | 2026-06-21                                                     |
| Plan reference     | `phenotype-registry/docs/operations/p5-4-phenoroutermonitor-absorption-2026-06-20.md` |

## Capability contract

The `phenoAI::router_monitor` capability exposes the same surface as
the prior `phenoRouterMonitor` crate:

- `RouterMonitor::observe(event: RouterEvent) -> Result<Receipt>`
- `RouterMonitor::flush() -> Result<Batch>`
- `RouterMonitor::subscribers() -> usize`

Telemetry payload schema (RouterEvent) is preserved byte-for-byte from
the prior crate. Consumers do not need adapter code — the repoint is
symbol-only at the import path level.

## Consumer repoint manifest

| Consumer repo        | Prior import                                    | New import                                            | Status      |
|----------------------|-------------------------------------------------|-------------------------------------------------------|-------------|
| `thegent`            | `phenoRouterMonitor::RouterMonitor`             | `phenoai::router_monitor::RouterMonitor`              | **PENDING** |
| `phenotype-registry` | (registry pointer)                              | (registry pointer)                                    | **DONE**    |
| `phenotype-otel`     | `phenoRouterMonitor` collector hook             | `phenoai::router_monitor` collector hook              | **PENDING** |

The `thegent` and `phenotype-otel` consumer repoints are tracked as
follow-up PRs in their respective repos. Both are 1-line import path
changes; no behavioral delta.

## Why no code moves

`phenoRouterMonitor` was a standalone crate (single-file, no
workspace deps). Absorbing it into `phenoAI` as a sub-module is the
correct end-state because:

1. **Single runtime**: the Phase 5 agent-runtime absorption sweep is
   consolidating all agent-adjacent crates under the `phenoAI` umbrella
   so consumers depend on one agent runtime, not a constellation of
   side-crates.
2. **Build graph**: removing the crate eliminates a workspace
   member and one `Cargo.toml`, simplifying the build.
3. **Telemetry graph**: the `phenoAI` umbrella already carries
   the routing hooks; adding a monitor module there keeps the
   telemetry in one crate instead of crossing crate boundaries.

## Out-of-scope

- **Behavioral changes**: the repoint is symbol-only; no schema,
  no rate-limiting, no telemetry-shape changes.
- **Schema versioning**: `RouterEvent` schema is preserved as v1
  to avoid breaking downstream consumers. A v2 schema is deferred
  to the `phenoai` v0.5 spec.
- **Removal of the old crate**: the `phenoRouterMonitor` repo is
  not deleted in this absorption. It is marked `archived` and the
  README points at `phenoAI` for new work. Final repo deletion is
  deferred to the Q3 archive cleanup.

## Related

- Phase 5 absorption plan: `phenotype-registry/docs/operations/p5-agent-runtime-absorption-2026-06-19.md`
- P5-4 spec: `phenotype-registry/docs/operations/p5-4-phenoroutermonitor-absorption-2026-06-20.md`
- P5-6 deferral: `phenotype-registry/docs/operations/p5-6-focalpoint-hexakit-deferred-2026-06-20.md`
- Companion absorption docs: `PHENOAGENT_ABSORPTION_2026_06_18.md`,
  `PHENOPROC_REPOINT.md`, `PHENOTYPE_HEXAKIT_REPOINT.md`
