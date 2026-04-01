# API Contract Audit Report - agentkit

## Executive Summary

Audit of all public API types for serialization schema coverage (serde derives) and contract completeness.

**Result: 6 types have serialization schemas, 12 types are missing them.**

---

## API Endpoints (Public Types)

### Traits (API Contracts)

| Trait | Module | Purpose | Schema |
|-------|--------|---------|--------|
| `Agent` | `domain::agents` | Main agent interface (`run`, `name`, `version`) | N/A (trait) |
| `Skill` | `domain::skills` | Modular capabilities (`name`, `description`, `execute`) | N/A (trait) |
| `Tool` | `domain::tools` | Tool integration with JSON schema params | N/A (trait) |
| `MemoryStore` | `domain::memory` | Persistent memory backend | N/A (trait) |
| `LLM` | `domain::ports` | Language model integration | N/A (trait) |
| `MemoryPort` | `domain::ports` | Memory access port | N/A (trait) |
| `ToolExecutor` | `domain::ports` | Tool execution port | N/A (trait) |

### Data Types WITH Serialization Schemas

| Type | Module | Serde Derives | Status |
|------|--------|---------------|--------|
| `MemoryEntry` | `domain::memory` | `Serialize, Deserialize` | OK |
| `MemoryRole` | `domain::memory` | `Serialize, Deserialize` | OK |
| `AgentStarted` | `domain::events` | `Serialize, Deserialize` | OK |
| `AgentCompleted` | `domain::events` | `Serialize, Deserialize` | OK |
| `ToolCalled` | `domain::events` | `Serialize, Deserialize` | OK |

### Data Types MISSING Serialization Schemas

| Type | Module | Fields | Priority |
|------|--------|--------|----------|
| `Context` | `domain::context` | `input`, `memory`, `tool_calls`, `tool_results`, `session_id`, `metadata` | HIGH |
| `Output` | `domain::context` | `content`, `tool_calls`, `metrics` | HIGH |
| `OutputContent` | `domain::context` | `Text(String)`, `Json(Value)`, `Error(String)` | HIGH |
| `ToolCall` | `domain::tools` | `name`, `params`, `id` | HIGH |
| `ToolResponse` | `domain::tools` | `id`, `result`, `error` | HIGH |
| `ToolCallOutput` | `domain::context` | `name`, `arguments`, `result` | MEDIUM |
| `ExecutionMetrics` | `domain::context` | `steps`, `tool_calls`, `duration_ms`, `tokens_used` | MEDIUM |
| `SkillResult` | `domain::skills` | `success`, `data`, `error` | MEDIUM |
| `AgentConfig` | `domain::agents` | `name`, `model`, `temperature`, `max_tokens`, `tools_enabled`, `memory_enabled` | MEDIUM |
| `AgentState` | `domain::agents` | `Idle`, `Thinking`, `Acting`, `WaitingForTool`, `Done`, `Error(String)` | LOW |
| `ExecutionStep` | `domain::agents` | `step_number`, `state`, `thought`, `action`, `observation` | LOW |
| `GenerationResult` | `domain::ports` | `content`, `tool_calls` | LOW |

---

## Gaps Found

### HIGH Priority - Core API Types Missing Serialization

1. **`Context`** - Primary input type for `Agent::run()`. Crosses the library boundary. Cannot be serialized for persistence, IPC, or debugging.

2. **`Output`** - Primary return type from `Agent::run()`. Cannot be serialized for response handling, logging, or storage.

3. **`OutputContent`** - Enum variant of `Output`. Missing `#[serde(tag)]` for proper enum serialization.

4. **`ToolCall`** - Used in tool invocation flow. Has JSON `params` field but struct itself has no schema.

5. **`ToolResponse`** - Return type from tool calls. Cannot be serialized for tool result persistence.

### MEDIUM Priority - Supporting Types Missing Serialization

6. **`ToolCallOutput`** - Used in `Output.tool_calls`. Missing schema despite being in response path.

7. **`ExecutionMetrics`** - Performance data. Only has `Default` derive, no serialization.

8. **`SkillResult`** - Return type from `Skill::execute()`. Cannot be serialized.

9. **`AgentConfig`** - Configuration type. Uses builder pattern but cannot be persisted/loaded.

### LOW Priority - Internal Types

10. **`AgentState`** - Internal state enum. May not need serialization unless state persistence is desired.

11. **`ExecutionStep`** - Tracing/debugging type. Low priority for serialization.

12. **`GenerationResult`** - LLM port return type. May need serialization if LLM results are persisted.

---

## Additional Observations

- **Tool `parameters()` method**: The `Tool` trait has a `parameters()` method that returns a JSON Schema `Value`. This is the only explicit schema definition in the codebase. Only `CalculatorTool` implements it. `WebSearchSkill` does NOT implement a `parameters()` equivalent.

- **No OpenAPI/Swagger**: No API documentation generation exists (expected for a Rust library).

- **Error types**: The `Error` enum uses `thiserror` but has no serde derives. Cannot be serialized for error response APIs.

- **No validation**: Types like `Context.input` and `ToolCall.params` accept arbitrary values without validation schemas.

---

## Recommendations

1. Add `#[derive(Serialize, Deserialize)]` to all HIGH priority types
2. Add `#[serde(tag = "type")]` to `OutputContent` enum for proper tagged serialization
3. Add `parameters()` method to `Skill` trait (mirroring `Tool::parameters()`)
4. Add serde derives to `Error` enum for serializable error responses
5. Consider adding validation via `validator` crate for `AgentConfig` and `Context`
