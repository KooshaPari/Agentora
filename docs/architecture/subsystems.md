# Subsystems — agent-platform

> L7 subsystem decomposition. Bounded contexts, ports, owned data, external
> dependencies, and failure modes for the agent-platform hexagonal adapter
> set. Companion to `AGENTS.md`. Initial decomposition 2026-06-21 (v16
> cycle-6 T1).

## Subsystem map

| Subsystem | Path | Responsibility | Owned data | Critical? |
|---|---|---|---|---|
| Runtime port | `ports/runtime.ts` | Defines the `Runtime` interface (the canonical agent loop contract) | none (interface only) | yes |
| Desktop stage port | `ports/desktop_stage.ts` | Surface for desktop-runtime adapters (window, IPC) | none (interface only) | yes |
| Device stage port | `ports/device_stage.ts` | Surface for device-runtime adapters (mobile, IoT) | none (interface only) | yes |
| Telemetry port | `ports/telemetry.ts` | OTLP / trace-emission surface for all adapters | none (interface only) | no |
| Adapter: Browser | `ports/adapters/browser.ts` | Browser automation via CDP/Playwright | session cookies, profiles | no |
| Adapter: Claude | `ports/adapters/claude.ts` | Claude API client adapter | API key ref, model alias | no |
| Adapter: Codex | `ports/adapters/codex.ts` | OpenAI Codex adapter | API key ref, model alias | no |
| Adapter: Desktop | `ports/adapters/desktop.ts` | Local desktop CLI wrapper (forks `desktop` binary) | argv, env filter | yes |
| Adapter: Eidolon | `ports/adapters/eidolon.ts` | Eidolon `Stage` adapter (delegates to EidolonTransport) | endpoint URL, session token | yes |
| Adapter: Forge | `ports/adapters/forge.ts` | Forge CLI dispatch (headless worker) | dispatch profile | no |
| Adapter: Mobile | `ports/adapters/mobile.ts` | Mobile device automation (delegates to mobile-cli/mobile-mcp) | device list cache | yes |
| Adapter: Sandbox | `ports/adapters/sandbox.ts` | Landlock/seccomp wrapper for adapter invocations | profile set, capability tokens | no |
| Examples | `examples/` | Runnable usage examples per adapter | none | no |

## Port catalogue

### Input ports (consumed)

- `pheno-errors::Error` envelope (TS binding).
- `pheno-config::Config` (TS via `Configra`).
- `pheno-tracing` OTLP exporter.
- `eidolon-core::Stage` — desktop/device adapters bind to this.

### Output ports (produced)

- `ports/runtime.ts::Runtime` — single trait every adapter implements.
- `ports/desktop_stage.ts::DesktopStage`.
- `ports/device_stage.ts::DeviceStage`.
- `ports/telemetry.ts::Telemetry`.

## External dependencies

| Dependency | Kind | Used by |
|---|---|---|
| `pheno-errors` | npm `@phenotype/errors` | error envelope |
| `pheno-config` | npm `@phenotype/config` | config cascade |
| `pheno-tracing` | npm `@phenotype/tracing` | OTLP spans |
| `eidolon` | npm `@phenotype/eidolon` (shim) | Eidolon stage |
| `mobile-cli` | Go binary (subprocess) | device discovery |
| `mobile-mcp` | npm `@phenotype/mobile-mcp` | device automation |
| `forge` | npm `forge-cli` | dispatch |
| `playwright` | npm | browser adapter |
| `node-fetch` / undici | stdlib | HTTP I/O |

## Failure modes

| Subsystem | Failure | Detection | Recovery |
|---|---|---|---|
| Runtime | Adapter returns malformed response | zod schema parse | throw `RuntimeError::Schema` |
| Desktop | binary not on PATH | ENOENT at fork | emit `AdapterMissing`; caller picks fallback |
| Mobile | device list cache stale | 410 Gone from mobile-mcp | re-fetch on next call |
| Eidolon | endpoint unreachable | connection refused / 5xx | exponential backoff; max 3 retries |
| Forge | dispatch profile not found | 404 from OmniRoute | fallback to `default` profile |
| Sandbox | capability denied | non-zero exit + Landlock error | re-spawn with relaxed profile; surface warning |
| Browser | session cookie expired | 401 from origin | re-auth via stored refresh token |

## Change log

- 2026-06-21 — initial decomposition (v16 cycle-6 T1, L7).