# Agentora — CLAUDE.md

> Hexagonal architecture Rust framework for building AI agents with skill systems,
> tool registries, and memory management. Package name: `agentkit`.

## Project Overview

| Field | Value |
|-------|-------|
| Package | `agentkit` |
| Repository | KooshaPari/Agentora |
| License | MIT OR Apache-2.0 |
| Edition | 2021 |
| Stack | Rust (tokio, async-trait, serde, thiserror, tracing) |

## Architecture

**4-layer hexagonal (ports & adapters)**:

```
src/
├── domain/         # Pure domain — no external deps (serde, thiserror, async-trait only)
│   ├── agents/     # Agent trait, AgentConfig, AgentState, ExecutionStep
│   ├── skills/     # Skill trait, SkillResult, SkillRegistry, WebSearchSkill
│   ├── tools/      # Tool trait, ToolCall, ToolResponse, ToolRegistry, CalculatorTool
│   ├── memory/     # MemoryEntry, MemoryRole, ShortTermMemory, MemoryStore, InMemoryStore
│   ├── context/   # Context, Output, OutputContent, ExecutionMetrics
│   ├── ports/     # LLM, MemoryPort, ToolExecutor traits
│   ├── events/    # AgentStarted, AgentCompleted, ToolCalled (serializable)
│   └── errors/    # Domain error enum
├── application/    # AgentExecutor, SimpleAgent
├── adapters/      # LLM + memory adapter implementations (placeholder)
└── infrastructure/ # Unified Error enum and Result type alias
```

### Dependency Flow

```
domain (no external deps) ← application ← adapters ← infrastructure
```

## Feature Flags

| Flag | Description | Extra deps |
|------|-------------|------------|
| `openai` | OpenAI API support | `reqwest 0.13` |
| `redis-memory` | Redis memory backend | `redis 0.23` |
| `sqlite-memory` | SQLite memory backend | `rusqlite 0.29` |

## Key Commands

```bash
# Build
cargo build

# Run tests
cargo test

# Format
cargo fmt --check

# Lint
cargo clippy --all-targets --all-features -- -D warnings

# Run binary
cargo run --bin agentkit

# Full quality gate
cargo fmt --check && cargo clippy --all-targets --all-features -- -D warnings && cargo test
```

## Quality Gates

- `cargo fmt --check` — formatting must pass
- `cargo clippy --all-targets --all-features -- -D warnings` — zero lints allowed
- `cargo test` — all tests must pass
- Proptest + mockall are available in `[dev-dependencies]`

## Core Traits

| Trait | Purpose |
|-------|---------|
| `Agent` | Main agent interface (`run(&self, ctx: &Context) -> Result<Output>`) |
| `Skill` | Modular, composable agent capabilities |
| `Tool` | Extensible tool integration with JSON schema parameter support |
| `MemoryStore` | Long-term memory backend (implement for any storage) |
| `LLM` | Language model port (implement for any provider) |
| `MemoryPort` | Memory access port |
| `ToolExecutor` | Tool execution port |

## Key Types

| Type | Description |
|------|-------------|
| `Context` | Passed to `Agent::run` — input, memory, tool calls, session_id, metadata |
| `Output` | Returned from `Agent::run` — content (Text/Json/Error), tool_calls, metrics |
| `AgentConfig` | Builder-pattern config (model, temperature) |
| `MemoryEntry` | Memory record with role (System/User/Assistant/Tool), content, timestamp |
| `Error` | Unified error enum with domain variants (Agent, Skill, Tool, Memory, LLM, Config, Execution) |

## Built-in Implementations

| Type | Name | Note |
|------|------|------|
| Skill | `WebSearchSkill` | Placeholder |
| Tool | `CalculatorTool` | Placeholder math evaluator |
| MemoryStore | `InMemoryStore` | In-memory for testing |
| Agent | `SimpleAgent` | Echo agent |

## Documentation

- Crate docs: `https://docs.rs/agentkit`
- API reference: doc comments on all public items

## Security & Compliance

- `deny.toml` + `cargo-deny.yml` (CI) enforce dependency audit
- Run `cargo deny check` locally before opening PRs
