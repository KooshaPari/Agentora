# Traceability Index — FR → test → impl

> Phase 3 traceability layer for the `agentkit` crate. Each functional
> requirement in `docs/specs/FR.md` is mapped to the acceptance tests
> that exercise it and to the implementation files that realize it.
> Tests live in `tests/` and are named `test_<topic>.rs`; each test
> carries a leading comment that repeats the FR id it verifies.
> Impl files live under `src/`. The crate name is `agentkit`; the
> repository slug is `Agentora`.

## Matrix

| FR       | Acceptance test(s)                                | Implementation file(s)                                                                              |
|----------|---------------------------------------------------|------------------------------------------------------------------------------------------------------|
| FR-001   | `tests/test_agent_dispatch.rs`                    | `src/domain/agents/mod.rs`, `src/domain/context/mod.rs`, `src/application/mod.rs`, `src/lib.rs`       |
| FR-002   | `tests/test_skill_registry.rs`                    | `src/domain/skills/mod.rs`                                                                           |
| FR-003   | `tests/test_tool_registry.rs`                     | `src/domain/tools/mod.rs`                                                                            |
| FR-004   | `tests/test_memory_tiers.rs`                      | `src/domain/memory/mod.rs`, `src/adapters/memory/mod.rs`                                             |
| FR-005   | `tests/test_executor_and_ports.rs`                | `src/application/mod.rs`, `src/domain/ports/mod.rs`, `src/adapters/llm/mod.rs`, `src/adapters/memory/mod.rs`, `src/lib.rs` |
| NFR-001  | `tests/test_hexagonal_boundary.rs`                | `src/domain/mod.rs`, `src/application/mod.rs`, `src/adapters/mod.rs`, `src/lib.rs`                   |
| NFR-002  | `tests/test_feature_flags.rs`                     | `Cargo.toml`                                                                                         |
| NFR-003  | `tests/test_deterministic_surface.rs`             | `src/adapters/llm/mod.rs`, `src/adapters/memory/mod.rs`, `src/domain/memory/mod.rs`                  |
| NFR-004  | `tests/test_async_send_sync.rs`                   | `src/domain/agents/mod.rs`, `src/domain/skills/mod.rs`, `src/domain/tools/mod.rs`, `src/domain/ports/mod.rs` |

## Per-FR detail

### FR-001 — Agent dispatch

- Trait: `Agent` at `src/domain/agents/mod.rs:7-21`.
- I/O: `Context`/`Output`/`OutputContent` at `src/domain/context/mod.rs:6-102`.
- Use-case: `AgentExecutor::run` at `src/application/mod.rs:40-49`.
- Built-in agent: `SimpleAgent` at `src/application/mod.rs:60-72`.
- Re-export: `src/lib.rs:20-25`.
- Test surface: `tests/test_agent_dispatch.rs`.

### FR-002 — Skill registry

- Trait: `Skill` at `src/domain/skills/mod.rs:9-21`.
- Result type: `SkillResult` at `src/domain/skills/mod.rs:23-47`.
- Registry: `SkillRegistry` at `src/domain/skills/mod.rs:49-87`.
- Built-in: `WebSearchSkill` at `src/domain/skills/mod.rs:89-114`.
- Test surface: `tests/test_skill_registry.rs`.

### FR-003 — Tool registry

- Call/Response: `ToolCall`/`ToolResponse` at `src/domain/tools/mod.rs:9-50`.
- Trait: `Tool` at `src/domain/tools/mod.rs:52-74`.
- Registry: `ToolRegistry` at `src/domain/tools/mod.rs:76-126`.
- Built-in: `CalculatorTool` at `src/domain/tools/mod.rs:128-178`.
- Test surface: `tests/test_tool_registry.rs`.

### FR-004 — Two-tier memory

- Entry types: `MemoryEntry`/`MemoryRole` at `src/domain/memory/mod.rs:6-51`.
- Ring buffer: `ShortTermMemory` at `src/domain/memory/mod.rs:53-95`.
- Store trait: `MemoryStore` at `src/domain/memory/mod.rs:97-107`.
- In-memory backend: `InMemoryStore` at `src/domain/memory/mod.rs:109-144`.
- Long-term wrapper: `LongTermMemory` at `src/domain/memory/mod.rs:146-167`.
- Thread-safe adapter: `InMemoryAdapter` at `src/adapters/memory/mod.rs:18-64`.
- Test surface: `tests/test_memory_tiers.rs`.

### FR-005 — Orchestration and ports

- `AgentExecutor` at `src/application/mod.rs:11-58`.
- `AgentConfig` at `src/domain/agents/mod.rs:23-64`.
- LLM port: `LLM` at `src/domain/ports/mod.rs:7-44`.
- Memory port: `MemoryPort` at `src/domain/ports/mod.rs:46-56`.
- Tool-executor port: `ToolExecutor` at `src/domain/ports/mod.rs:58-62`.
- Echo LLM adapter: `EchoLLM` at `src/adapters/llm/mod.rs:28-68`.
- OpenAI adapter (feature `openai`): `OpenAIChatLLM` at
  `src/adapters/llm/mod.rs:70-314`.
- Redis adapter (feature `redis-memory`): `RedisMemoryAdapter` at
  `src/adapters/memory/mod.rs:68-145`.
- SQLite adapter (feature `sqlite-memory`): `SqliteMemoryAdapter` at
  `src/adapters/memory/mod.rs:149-282`.
- Re-exports: `src/lib.rs:11-25`.
- Test surface: `tests/test_executor_and_ports.rs`.

### NFR-001 — Hexagonal boundary

- Module root: `src/domain/mod.rs:5-12` declares the domain submodules
  and forbids upward imports.
- Application depends only on domain: `src/application/mod.rs:3-6`.
- Adapters depend on `domain::ports` only:
  `src/adapters/llm/mod.rs:19-20` and
  `src/adapters/memory/mod.rs:13-15`.
- Re-exports: `src/lib.rs:6-25`.
- Test surface: `tests/test_hexagonal_boundary.rs`.

### NFR-002 — Feature-flag isolation

- `Cargo.toml:39-43` declares `reqwest`, `redis`, and `rusqlite` as
  optional dependencies.
- `Cargo.toml:52-56` declares the `openai`, `redis-memory`, and
  `sqlite-memory` features.
- Adapters gate their code with `#[cfg(feature = "...")]`:
  `src/adapters/llm/mod.rs:71-314` and
  `src/adapters/memory/mod.rs:68-282`.
- Test surface: `tests/test_feature_flags.rs`.

### NFR-003 — Deterministic test surface

- `EchoLLM` at `src/adapters/llm/mod.rs:28-68`.
- `InMemoryStore` at `src/domain/memory/mod.rs:109-144`.
- `InMemoryAdapter` at `src/adapters/memory/mod.rs:18-64`.
- Test surface: `tests/test_deterministic_surface.rs`.

### NFR-004 — Async, `Send + Sync`

- `Agent` is `#[async_trait]` and `Send + Sync` at
  `src/domain/agents/mod.rs:7-21`.
- `Skill` is `#[async_trait]` and `Send + Sync` at
  `src/domain/skills/mod.rs:9-21`.
- `Tool` is `#[async_trait]` and `Send + Sync` at
  `src/domain/tools/mod.rs:52-74`.
- `LLM` is `#[async_trait]` and `Send + Sync` at
  `src/domain/ports/mod.rs:7-21`.
- `ToolExecutor` is `#[async_trait]` and `Send + Sync` at
  `src/domain/ports/mod.rs:58-62`.
- Test surface: `tests/test_async_send_sync.rs`.

## Coverage

- FRs covered by ≥1 test: **5 / 5** (FR-001..FR-005).
- NFRs covered by ≥1 test: **4 / 4** (NFR-001..NFR-004).
- Test files in `tests/`: **9** (≥ the 5-test minimum required for Phase 3).
- Implementation files referenced: `Cargo.toml`, `src/lib.rs`, every file
  in `src/domain/`, `src/application/`, `src/adapters/llm/`, and
  `src/adapters/memory/`.
