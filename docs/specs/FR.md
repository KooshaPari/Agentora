# Functional Requirements — agentkit (Agentora)

> Phase 3 spec layer for the `agentkit` crate. Every FR is derived from a
> concrete surface in the codebase (`src/domain/**`, `src/application/**`,
> `src/adapters/**`, `src/lib.rs`). Each FR is mapped to one or more
> acceptance tests in `tests/` and to the source files that implement it;
> see `docs/specs/TRACEABILITY.md` for the full FR → test → impl matrix.

## Scope

`agentkit` is a Rust hexagonal (ports & adapters) framework for building AI
agents. It exposes:

- `domain::agents::Agent` — async agent trait (`run`, `name`, `version`)
- `domain::skills::Skill` + `SkillRegistry` — pluggable capabilities
- `domain::tools::Tool` + `ToolRegistry` — JSON-schema tool invocations
- `domain::memory::ShortTermMemory` (ring buffer) and
  `LongTermMemory<S: MemoryStore>` (persistent)
- `domain::context::{Context, Output, OutputContent, ExecutionMetrics}` — I/O
- `domain::ports::{LLM, MemoryPort, ToolExecutor}` — adapter contracts
- `domain::events::{AgentStarted, AgentCompleted, ToolCalled}` — lifecycle
- `application::AgentExecutor` + `SimpleAgent` — use-case orchestrator
- `adapters::llm::{EchoLLM, OpenAIChatLLM}` and
  `adapters::memory::{InMemoryAdapter, RedisMemoryAdapter, SqliteMemoryAdapter}`

## Functional Requirements

### FR-001 — Agent dispatch (`Agent::run` with `Context` → `Output`)

The system shall expose an async `Agent` trait whose `run(&Context) -> Result<Output>`
method is the primary entry point for executing an agent. The agent receives
a `Context` containing the user `input`, prior `memory` entries, recorded
`tool_calls` and `tool_results`, a `session_id`, and arbitrary `metadata`.
The agent returns an `Output` containing an `OutputContent` (Text | Json |
Error), a list of `ToolCallOutput` records, and `ExecutionMetrics`.

- Surfaced in `src/domain/agents/mod.rs:7-21` (trait) and
  `src/domain/context/mod.rs:6-44` (Context).
- Orchestrated by `src/application/mod.rs:40-49` (`AgentExecutor::run`) and
  `src/application/mod.rs:60-72` (`SimpleAgent`).

### FR-002 — Skill registry with unique names and JSON parameters

The system shall provide a `SkillRegistry` that allows registering `Skill`
trait implementations, looking them up by name, listing all registered
skills, and querying presence. Registering a skill whose name is already
present shall fail with `Error::Skill(...)`. Each `Skill::execute` shall
accept a `serde_json::Value` parameter object and return a `SkillResult`
that carries `success`, `data`, and an optional `error` string.

- Surfaced in `src/domain/skills/mod.rs:9-87` (trait, SkillResult,
  SkillRegistry) and `src/domain/skills/mod.rs:90-114`
  (`WebSearchSkill`).

### FR-003 — Tool registry with JSON-schema parameters and tool dispatch

The system shall provide a `ToolRegistry` that registers `Tool`
implementations, looks them up by name, lists registered tools, and
answers `has(name)`. The `Tool::parameters` method shall expose a
JSON-schema describing the expected input. `ToolRegistry::call` shall
resolve a `ToolCall` (name + params + id) to a `ToolResponse`
(success or failure with the call's id preserved) and shall return
`Error::Tool(...)` when the named tool is not registered.

- Surfaced in `src/domain/tools/mod.rs:9-126` (ToolCall, ToolResponse,
  Tool, ToolRegistry) and `src/domain/tools/mod.rs:129-178`
  (`CalculatorTool`).

### FR-004 — Two-tier memory: short-term ring buffer + long-term store

The system shall provide a `ShortTermMemory` ring buffer with a
configurable `limit` that auto-evicts the oldest entry when the limit is
exceeded, and a `LongTermMemory<S: MemoryStore>` wrapper that delegates
to a pluggable store. The `MemoryStore` trait shall support
`save(&MemoryEntry) -> Result<(), String>`, `search(query, limit) ->
Result<Vec<MemoryEntry>, String>`, and `clear() -> Result<(), String>`.
`MemoryEntry` shall be `Serialize`/`Deserialize`, carry a `MemoryRole`
(System | User | Assistant | Tool), a `content` string, a UTC
`timestamp`, and a `metadata: serde_json::Value`.

- Surfaced in `src/domain/memory/mod.rs:6-167`
  (`MemoryEntry`, `MemoryRole`, `ShortTermMemory`, `MemoryStore`,
  `InMemoryStore`, `LongTermMemory`).

### FR-005 — Application orchestration (`AgentExecutor`) and adapter ports

The system shall provide an `AgentExecutor` in the application layer that
accepts an `AgentConfig` and optional `SkillRegistry` / `ToolRegistry`
instances via builder methods, exposes the configured tool and skill
names, and runs an agent on an input string by constructing a `Context`
and pre-seeding it with a system `MemoryEntry` before invoking
`agent.run(&ctx)`. The system shall additionally expose three port
traits — `LLM`, `MemoryPort`, and `ToolExecutor` — that adapters in
`src/adapters/**` implement, with concrete adapters for echo LLM
(default), OpenAI Chat Completions (feature `openai`), in-memory
memory (default), Redis memory (feature `redis-memory`), and SQLite
memory (feature `sqlite-memory`).

- Surfaced in `src/application/mod.rs:11-58` (`AgentExecutor`),
  `src/domain/ports/mod.rs:7-62` (LLM, MemoryPort, ToolExecutor ports),
  `src/adapters/llm/mod.rs:29-340` (EchoLLM, OpenAIChatLLM), and
  `src/adapters/memory/mod.rs:18-282` (InMemoryAdapter, RedisMemoryAdapter,
  SqliteMemoryAdapter).

## Non-Functional Requirements (NFRs)

### NFR-001 — Hexagonal boundary enforcement

Domain code (`src/domain/**`) must not import from `src/adapters/**` or
`src/infrastructure/**`. The dependency flow is strictly:
`domain ← application ← adapters`, with `infrastructure` providing
shared `Error`/`Result` re-exports.

### NFR-002 — Feature-flag isolation for heavy backends

Heavy runtime dependencies (`reqwest`, `redis`, `rusqlite`) must be
gated behind the `openai`, `redis-memory`, and `sqlite-memory` cargo
features respectively, and must not appear in the default build.

### NFR-003 — Deterministic test surface

All adapters that talk to the network or to external stores
(`OpenAIChatLLM`, `RedisMemoryAdapter`, `SqliteMemoryAdapter`) must
expose deterministic in-tree alternatives (`EchoLLM`,
`InMemoryAdapter`, `InMemoryStore`) so that the default test suite
runs without network, Docker, or external services.

### NFR-004 — Async, `Send + Sync` core traits

`Agent`, `Skill`, `Tool`, `LLM`, and `ToolExecutor` are declared
`#[async_trait]` and required to be `Send + Sync`, so the framework
remains usable from `tokio::main` and embeddable inside multi-threaded
runtimes.

## phenoRouterMonitor → phenoAI absorption requirements (FR-LLM)

These requirements are added by the P5-4 absorption plan
(`docs/operations/p5-agent-runtime-absorption-2026-06-19.md`,
rows 21, 25) and describe the contract that the absorbed
`phenoRouterMonitor` crate must satisfy now that it lives in
`phenoAI`. See `docs/absorption/PHENOROUTERMONITOR_REPOINT.md` for
the full repoint rationale.

### FR-LLM-001 — phenoRouterMonitor CRATE re-homed under phenoAI

`phenoRouterMonitor` is no longer a standalone KooshaPari repository.
Its sources, CI workflows, ADRs, and traceability rows are re-homed
under `KooshaPari/phenoAI` (this repository) as a workspace member
or a `crates/` subdirectory. The crate is renamed `phenoai-router`
(or the chosen scoped name) and exposes the same public API surface
that consumers depended on before the move.

### FR-LLM-002 — phenoAI exposes the routing trait surface

`phenoAI` exposes the routing trait surface that `phenoRouterMonitor`
used to expose (router config, route selection, request envelope).
Existing callers repoint their dependency from the archived
`phenoRouterMonitor` crate to the in-tree `phenoAI` module with
no source-level API change beyond the package import path.

### FR-LLM-003 — phenoAI inherits the phenoRouterMonitor ADR set

The ADRs that used to live at `KooshaPari/phenoRouterMonitor/docs/adrs/`
are folded into `phenoAI/docs/adrs/` and cross-linked from the
`phenoAI` README. The disposition of each ADR (kept, superseded,
re-issued) is recorded in `docs/specs/TRACEABILITY.md`.

### FR-LLM-004 — phenoAI Tier-1 governance coverage

The absorbed `phenoRouterMonitor` workspace inherits the Tier-1
governance gate set used by `phenoAI` (workflows, deny, gitleaks,
CODEOWNERS, secretscan). The gate-flip is recorded in
`registry/disposition-index.json` under `gate-phenoRouterMonitor`
with status `absorbed-by:phenoai`.

## Acceptance test mapping (overview)

Each FR has at least one acceptance test in `tests/` whose name
contains the FR id and whose leading comment repeats the FR id. The
mapping is:

| FR         | Test files                                                    |
|------------|---------------------------------------------------------------|
| FR-001     | `tests/test_agent_dispatch.rs`                                |
| FR-002     | `tests/test_skill_registry.rs`                                |
| FR-003     | `tests/test_tool_registry.rs`                                 |
| FR-004     | `tests/test_memory_tiers.rs`                                  |
| FR-005     | `tests/test_executor_and_ports.rs`                            |
| FR-LLM-001 | `crates/phenoai-router/tests/repoint_smoke.rs` (added in P5-4) |
| FR-LLM-002 | `crates/phenoai-router/tests/router_trait.rs` (added in P5-4)  |
| FR-LLM-003 | `docs/absorption/PHENOROUTERMONITOR_REPOINT.md` cross-link     |
| FR-LLM-004 | `registry/disposition-index.json` `gate-phenoRouterMonitor` row |

See `docs/specs/TRACEABILITY.md` for the FR → test → impl matrix and
any impl files that are not under `src/`.
