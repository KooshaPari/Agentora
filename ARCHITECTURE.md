# Architecture

## Overview

Rust framework for building AI agents. Hexagonal (ports & adapters) architecture with a 4-layer design: domain, application, adapters, infrastructure. Package name: `agentkit`.

## Components

### Domain Layer (`src/domain/`) — Pure, no external deps
- `agents/` — Agent trait, AgentConfig, AgentState, ExecutionStep
- `skills/` — Skill trait, SkillResult, SkillRegistry, WebSearchSkill
- `tools/` — Tool trait, ToolCall, ToolResponse, ToolRegistry, CalculatorTool
- `memory/` — MemoryEntry, MemoryRole, ShortTermMemory, MemoryStore, InMemoryStore
- `context/` — Context, Output, OutputContent, ExecutionMetrics
- `ports/` — LLM, MemoryPort, ToolExecutor traits
- `events/` — Serializable domain events (AgentStarted, AgentCompleted, ToolCalled)
- `errors/` — Domain error enum (thiserror)

### Application Layer (`src/application/`)
AgentExecutor orchestrates agents with skills, tools, and memory. SimpleAgent is a built-in echo agent.

### Adapters Layer (`src/adapters/`)
Pluggable implementations: LLM adapters, memory adapters. Backends via feature flags (`openai`, `redis-memory`, `sqlite-memory`).

### Infrastructure Layer (`src/infrastructure/`)
Unified Error enum and Result type alias.

## Data Flow

`Agent::run(ctx: &Context)` -> domain logic -> LLM port (adapter) -> tool execution (via ToolExecutor port) -> memory (via MemoryPort) -> `Output`.

## Key Files

- `src/domain/` — pure domain types and traits
- `src/application/` — orchestration
- `src/adapters/` — external integrations
- `Cargo.toml` — workspace manifest
- Feature flags: `openai`, `redis-memory`, `sqlite-memory`
