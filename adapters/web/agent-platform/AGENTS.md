# AGENTS.md — KooshaPari/agent-platform

**Status:** ACTIVE substrate — interface domain only.
**Governance:** [ADR-023 (agent-effort governance)](../../../../../../docs/adr/2026-06-15/ADR-023-agent-effort-governance.md) at the monorepo root.
**Domain plan:** [findings/2026-06-17-agent-platform-domain.md](../../../../../../findings/2026-06-17-agent-platform-domain.md).

---

## Project overview

`agent-platform` is the **single coordination point** between an agent runtime
(Forge / Codex / Claude) and any device modality an agent might drive. It
defines a hexagonal **ports layer** (TypeScript traits) plus pluggable
**adapters** that satisfy those traits against concrete backends
(Eidolon for native device control, Playwright for the browser, ADB for
Android, MCP-stdio for iOS). Domain code in the rest of the fleet depends
on the ports here, never on the backends directly. Per ADR-023 Rule 3,
this is the canonical substrate for agent-runtime ↔ device interactions;
no equivalent code should be re-introduced in a per-app `lib/`,
`crates/`, or `phenoShared/`.

## What is in this repo

```
ports/                          <-- the entire surface area of this repo
  device_stage.ts               DeviceStage — the abstract trait every modality adapter must satisfy
  desktop_stage.ts              DesktopStage — structural sub-trait (extends DeviceStage)
  runtime.ts                    AgentRuntime — abstract trait for agent runtime adapters
  telemetry.ts                  OTLP span helpers (graceful no-op when @opentelemetry/api absent)
  adapters/
    eidolon.ts                  EidolonStage + EidolonTransport (stdio / http / Null) — the canonical adapter
    desktop.ts                  DesktopStageAdapter — Eidolon-backed DesktopStage impl
    mobile.ts                   MobileDeviceAdapter — ADB + mobile-mcp transports + Null fallback
    sandbox.ts                  SandboxAdapter — Eidolon sandbox + Null fallback
    browser.ts                  BrowserAdapter — Playwright MCP + Null fallback
    codex.ts / claude.ts / forge.ts  AgentRuntime adapters (one per agent runtime)
  tests/                        vitest suites covering every trait + adapter
```

**Not in this repo (intentionally):**

- No business logic — pure port / adapter / test code.
- No UI — no React, no Tailwind, no JSX/TSX.
- No persistent storage — sessions are owned by the underlying transport.
- No `phenoShared/`, no per-app `crates/`, no `random lib/` (ADR-023 Rule 3).

## Device modalities covered

| Modality | Trait | Production adapter | Backend |
|---|---|---|---|
| **Mobile** (Android + iOS) | `DeviceStage` | `MobileDeviceAdapter` (`ports/adapters/mobile.ts`) | ADB (Android) + `mobile-mcp` MCP server (iOS) |
| **Desktop** (macOS + Linux + Windows) | `DesktopStage` (sub-trait of `DeviceStage`) | `DesktopStageAdapter` (`ports/adapters/desktop.ts`) | `EidolonStage` → `KooshaPari/Eidolon eidolon-desktop` (Core Graphics / xdotool) |
| **Sandbox** (VM, Docker, Firecracker, gVisor) | `DeviceStage` | `SandboxAdapter` (`ports/adapters/sandbox.ts`) | `EidolonSandboxTransport` → Eidolon MCP |
| **Browser** (Chromium, Firefox, WebKit) | `DeviceStage` | `BrowserAdapter` (`ports/adapters/browser.ts`) | `PlaywrightMcpTransport` → Playwright MCP server |

All four modalities go through the **single canonical transport hub**
`EidolonStage` (`ports/adapters/eidolon.ts`) when the Eidolon MCP server
is reachable. The non-Eidolon adapters (mobile ADB, Playwright) are
swappable fallbacks and direct integrations — they exist so an agent
runtime can drive a device without first standing up Eidolon.

`AgentRuntime` (separate port in `ports/runtime.ts`) covers the
agent-runtime side: `ForgeRuntime`, `CodexRuntime`, `ClaudeRuntime`
(`ports/adapters/{forge,codex,claude}.ts`).

## How to add a new modality (port + adapter + test)

1. **Port first.** Add a new file under `ports/` (e.g.
   `wearable_stage.ts`) that defines a structural trait extending
   `DeviceStage` (or a sibling trait if the modality does not fit
   `DeviceStage`'s session-based shape). Re-export the branded id
   types (`DeviceId`, `SessionId`, etc.) so consumers do not need to
   import from `device_stage.ts` directly. Pattern reference:
   `ports/desktop_stage.ts` (a sub-trait with modality-locked
   `modality: "desktop"`).
2. **Adapter second.** Add `ports/adapters/wearable.ts` with an
   `class WearableStageAdapter implements WearableStage`. Pick the
   backend transport: reuse `EidolonTransport` (preferred — keeps the
   Eidolon MCP path canonical) or implement a new transport that
   satisfies the local `Transport` interface. Always wire
   `getTracer().startSpan(...)` around each method (see
   `ports/adapters/eidolon.ts` for the OTLP pattern).
3. **Null fallback.** Every adapter MUST expose a `NullXyzTransport`
   that returns `{ ok: false, error: "..." }` for every call, so
   domain code can depend on the trait being present even when no
   backend is configured. ADR-023 Rule 3.1 quality bar: the adapter
   is safe to inject without a live backend.
4. **Test third.** Add `ports/tests/wearable.test.ts` (vitest) that
   exercises the structural trait + null fallback + at least one happy
   path through a mocked transport. `vitest.config.ts` auto-discovers
   `ports/tests/**/*.test.ts`.
5. **Wire into AGENTS.md.** Add a row to the "Device modalities
   covered" table above and link to the new adapter file.

## How to add a new transport (extend EidolonTransport)

1. Add a new `class XxxTransport implements EidolonTransport` in
   `ports/adapters/eidolon.ts` (or a sibling file under
   `ports/adapters/` if the transport is not Eidolon-flavored).
2. The transport must satisfy `EidolonTransport.call<T>(method, params)`
   returning `Promise<McpResult<T>>` where `McpResult<T> = { ok, data?, error? }`.
3. Wire the transport into `EidolonStage.initTransport(config)` (or the
   per-modality adapter's `initTransport`) so `EidolonStageConfig.transport`
   can select it via a string literal union.
4. Add a `ports/tests/eidolon_<transport>.test.ts` that verifies the
   null-fallback contract AND at least one successful round-trip against
   a `fetch`-mocked server. No real network in unit tests.

## Conventions

- **Language:** TypeScript ES2022 / strict mode (`tsconfig.json`).
- **Package manager:** npm (uses `package-lock.json`).
- **Tests:** vitest. Run `npm test` from the repo root. CI is not yet
  wired (TODO — ADR-023 Rule 3.1 item 7).
- **Type checks:** `npm run check` runs `tsc --noEmit`.
- **Telemetry:** every adapter method wraps `getTracer().startSpan(...)`
  and records errors via `span.recordError(...)`. OTLP export is the
  consumer's responsibility — this repo only emits the spans.
- **Branded ids:** all identifier types (`DeviceId`, `SessionId`,
  `StageId`, `AgentId`, `ModelId`, `DisplayId`) are branded strings
  (`string & { readonly __brand: "..." }`). Do not relax this.
- **Conventional commits** on all branches: `feat(ports):`,
  `fix(adapters):`, `test(ports):`, `chore(governance):`, `docs(governance):`.
- **PR labels:** `governance` for ADR-driven cleanups; `L<n>-#<n>` for
  DAG tracking; `T66` for port work.

## Out of scope

- Agent runtime business logic → lives in `phenotype-hub` /
  `phenotype-bus` / per-app domain crates.
- Native device control → lives in `KooshaPari/Eidolon` (Rust).
- MCP server implementations → live in `KooshaPari/mobile-mcp` etc.
- Device-specific UI / rendering → lives in app-level repos
  (e.g. `Civis` is the only ACTIVE app consumer of `DeviceStage`).