# agentkit - Agent Framework

[![Build](https://img.shields.io/github/actions/workflow/status/KooshaPari/Agentora/ci.yml?branch=main&label=build)](https://github.com/KooshaPari/Agentora/actions)
[![Release](https://img.shields.io/github/v/release/KooshaPari/Agentora?include_prereleases&sort=semver)](https://github.com/KooshaPari/Agentora/releases)
[![License](https://img.shields.io/github/license/KooshaPari/Agentora)](LICENSE)
[![Phenotype](https://img.shields.io/badge/Phenotype-org-blueviolet)](https://github.com/KooshaPari)


> A hexagonal architecture framework for building AI agents with skill systems, tool registries, and memory management.

## Overview

agentkit is a Rust framework for building AI agents. It provides:

- **Skill System** — Modular, composable capabilities agents can use
- **Tool Registry** — Extensible tool integration with JSON schema support
- **Memory Management** — Two-tier memory (short-term ring buffer, long-term persistent stores)
- **Hexagonal Architecture** — Clean separation between domain, application, adapters, and infrastructure
- **Event System** — Serializable domain events for agent lifecycle tracking

## Installation

```toml
[dependencies]
agentkit = "0.1.0"
```

Or via CLI:

```bash
cargo add agentkit
```

### Feature Flags

| Feature | Description | Dependencies |
|---------|-------------|-------------|
| `openai` | OpenAI API support | `reqwest 0.11` |
| `redis-memory` | Redis memory backend | `redis 0.23` |
| `sqlite-memory` | SQLite memory backend | `rusqlite 0.29` |

```toml
[dependencies]
agentkit = { version = "0.1.0", features = ["openai", "sqlite-memory"] }
```

## Architecture

agentkit follows a **4-layer hexagonal (ports & adapters) architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer                                       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  AgentExecutor  │  SimpleAgent                       │ │
│  │  Orchestrates agents with skills, tools, and memory  │ │
│  └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  Domain Layer (Pure — no external dependencies)          │
│  ┌──────────┬──────────┬──────────┬──────────┬────────┐ │
│  │ agents/  │ skills/  │ tools/   │ memory/  │ ports/ │ │
│  │ context/ │ events/  │ errors/  │          │        │ │
│  └──────────┴──────────┴──────────┴──────────┴────────┘ │
├─────────────────────────────────────────────────────────┤
│  Adapters Layer (External implementations)               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  llm/   │  memory/   │  (pluggable backends)        │ │
│  └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  Infrastructure Layer (Cross-cutting concerns)           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  error.rs  (unified error types via thiserror)      │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Module Structure

```
agentkit/
├── Cargo.toml
├── src/
│   ├── lib.rs                    # Crate root, re-exports, prelude
│   ├── bin/
│   │   └── main.rs               # CLI binary entry point
│   ├── domain/
│   │   ├── mod.rs                # Domain module root
│   │   ├── agents/mod.rs         # Agent trait, AgentConfig, AgentState, ExecutionStep
│   │   ├── skills/mod.rs         # Skill trait, SkillResult, SkillRegistry, WebSearchSkill
│   │   ├── tools/mod.rs          # Tool trait, ToolCall, ToolResponse, ToolRegistry, CalculatorTool
│   │   ├── memory/mod.rs         # MemoryEntry, MemoryRole, ShortTermMemory, MemoryStore,
│   │   │                         # LongTermMemory<S>, InMemoryStore
│   │   ├── context/mod.rs        # Context, Output, OutputContent, ToolCallOutput, ExecutionMetrics
│   │   ├── ports/mod.rs          # LLM, MemoryPort, ToolExecutor traits, GenerationResult
│   │   ├── events/mod.rs         # AgentStarted, AgentCompleted, ToolCalled events
│   │   └── errors/mod.rs         # Domain error enum (thiserror)
│   ├── application/
│   │   └── mod.rs                # AgentExecutor, SimpleAgent
│   ├── adapters/
│   │   ├── mod.rs                # Adapters module root
│   │   ├── llm/mod.rs            # LLM adapter implementations (placeholder)
│   │   └── memory/mod.rs         # Memory adapter implementations (placeholder)
│   └── infrastructure/
│       ├── mod.rs                # Infrastructure module root
│       └── error.rs              # Unified Error enum and Result type alias
```

### Dependency Flow

```
domain ─── (no external deps beyond serde, thiserror, async-trait)
  ↑
application ─── depends on domain
  ↑
adapters ─── depends on domain ports
  ↑
infrastructure ─── provides shared error types
```

## Core Traits

### `Agent` — The main agent interface

Implement this to create an agent. The `run` method is the primary entry point.

```rust
#[async_trait]
pub trait Agent: Send + Sync {
    async fn run(&self, ctx: &Context) -> Result<Output>;
    fn name(&self) -> &str { "agent" }
    fn version(&self) -> &str { "1.0.0" }
}
```

| Method | Required | Description |
|--------|----------|-------------|
| `run` | Yes | Execute the agent with the given context |
| `name` | No | Agent identifier (default: `"agent"`) |
| `version` | No | Agent version (default: `"1.0.0"`) |

### `Skill` — Modular agent capabilities

Skills are self-contained capabilities that agents can invoke.

```rust
#[async_trait]
pub trait Skill: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> String { String::new() }
    async fn execute(&self, params: Value) -> Result<SkillResult>;
}
```

| Method | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Skill identifier |
| `description` | No | Human-readable description |
| `execute` | Yes | Run the skill with JSON parameters |

### `Tool` — Extensible tool integration

Tools are invoked by agents during execution, with JSON schema parameter support.

```rust
#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> String { String::new() }
    fn parameters(&self) -> Value { /* default JSON schema */ }
    async fn call(&self, call: ToolCall) -> Result<Value>;
}
```

| Method | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Tool identifier |
| `description` | No | Human-readable description |
| `parameters` | No | JSON Schema for tool parameters |
| `call` | Yes | Execute the tool with a ToolCall |

### `MemoryStore` — Long-term memory backend

Implement this to provide persistent memory storage.

```rust
pub trait MemoryStore: Send + Sync {
    fn save(&mut self, entry: &MemoryEntry) -> Result<(), String>;
    fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, String>;
    fn clear(&mut self) -> Result<(), String>;
}
```

### `LLM` — Language model port

Implement this to connect any LLM provider.

```rust
#[async_trait]
pub trait LLM: Send + Sync {
    async fn complete(&self, prompt: &str) -> Result<String>;
    async fn generate(&self, context: &Context) -> Result<String>;
    async fn generate_with_tools(
        &self,
        context: &Context,
        tools: Vec<serde_json::Value>,
    ) -> Result<GenerationResult>;
}
```

### `MemoryPort` — Memory access port

```rust
pub trait MemoryPort: Send + Sync {
    fn add(&self, entry: MemoryEntry) -> Result<()>;
    fn recent(&self, limit: usize) -> Result<Vec<MemoryEntry>>;
    fn search(&self, query: &str) -> Result<Vec<MemoryEntry>>;
}
```

### `ToolExecutor` — Tool execution port

```rust
#[async_trait]
pub trait ToolExecutor: Send + Sync {
    async fn execute(&self, call: ToolCall) -> Result<ToolResponse>;
}
```

## Key Types

### `Context` — Execution context

Passed to `Agent::run`. Contains user input, memory, tool calls, and metadata.

```rust
pub struct Context {
    pub input: String,
    pub memory: Vec<MemoryEntry>,
    pub tool_calls: Vec<ToolCall>,
    pub tool_results: Vec<ToolResponse>,
    pub session_id: String,
    pub metadata: HashMap<String, Value>,
}
```

### `Output` — Agent output

Returned from `Agent::run`. Contains content, tool calls, and execution metrics.

```rust
pub struct Output {
    pub content: OutputContent,      // Text(String) | Json(Value) | Error(String)
    pub tool_calls: Vec<ToolCallOutput>,
    pub metrics: ExecutionMetrics,
}
```

### `AgentConfig` — Agent configuration

Builder-pattern configuration for agents.

```rust
let config = AgentConfig::new("my-agent")
    .model("gpt-4")
    .temperature(0.3);
```

### `MemoryEntry` — Memory record

```rust
pub struct MemoryEntry {
    pub role: MemoryRole,            // System | User | Assistant | Tool
    pub content: String,
    pub timestamp: DateTime<Utc>,
    pub metadata: Value,
}

// Factory methods
MemoryEntry::user("Hello")
MemoryEntry::assistant("Hi there!")
MemoryEntry::system("You are a helpful assistant.")
```

### Error Types

```rust
#[derive(Error, Debug)]
pub enum Error {
    #[error("Agent error: {0}")]
    Agent(String),
    #[error("Skill error: {0}")]
    Skill(String),
    #[error("Tool error: {0}")]
    Tool(String),
    #[error("Memory error: {0}")]
    Memory(String),
    #[error("LLM error: {0}")]
    LLM(String),
    #[error("Config error: {0}")]
    Config(String),
    #[error("Execution error: {0}")]
    Execution(String),
}

pub type Result<T> = std::result::Result<T, Error>;
```

### Events

Serializable domain events for tracking agent lifecycle:

- `AgentStarted` — Agent began execution
- `AgentCompleted` — Agent finished (includes duration and step count)
- `ToolCalled` — A tool was invoked (includes arguments)

## Usage Examples

### Quick Start

```rust
use agentkit::prelude::*;
use agentkit::domain::agents::Agent;

struct MyAgent;

#[async_trait]
impl Agent for MyAgent {
    async fn run(&self, ctx: &Context) -> Result<Output> {
        Ok(Output::text(format!("Received: {}", ctx.input)))
    }

    fn name(&self) -> &str { "my-agent" }
}

#[tokio::main]
async fn main() -> Result<()> {
    let agent = MyAgent;
    let ctx = Context::new("Hello, world!");
    let output = agent.run(&ctx).await?;
    println!("{}", output.content);
    Ok(())
}
```

### Using AgentExecutor

`AgentExecutor` orchestrates agents with skills, tools, and memory:

```rust
use agentkit::prelude::*;

#[tokio::main]
async fn main() -> Result<()> {
    let config = AgentConfig::new("assistant")
        .model("gpt-4")
        .temperature(0.7);

    let executor = AgentExecutor::new(config);
    let output = executor.run(&SimpleAgent, "What is 2+2?".to_string()).await?;

    match output.content {
        OutputContent::Text(text) => println!("{}", text),
        _ => println!("Unexpected output type"),
    }

    Ok(())
}
```

### Registering Skills

```rust
use agentkit::domain::skills::{Skill, SkillResult, SkillRegistry};
use serde_json::{json, Value};

struct SummarizeSkill;

#[async_trait]
impl Skill for SummarizeSkill {
    fn name(&self) -> &str { "summarize" }

    fn description(&self) -> String {
        "Summarize a given text".to_string()
    }

    async fn execute(&self, params: Value) -> Result<SkillResult> {
        let text = params.get("text")
            .and_then(|v| v.as_str())
            .ok_or_else(|| Error::Skill("Missing 'text' parameter".into()))?;

        // Summarization logic here
        Ok(SkillResult::success(json!({
            "summary": format!("Summary of: {}", &text[..text.len().min(50)]))
        })))
    }
}

fn main() {
    let mut registry = SkillRegistry::new();
    registry.register(Box::new(SummarizeSkill)).unwrap();

    assert!(registry.has("summarize"));
    println!("Available skills: {:?}", registry.list());
}
```

### Registering Tools

```rust
use agentkit::domain::tools::{Tool, ToolCall, ToolRegistry};
use serde_json::{json, Value};

struct WeatherTool;

#[async_trait]
impl Tool for WeatherTool {
    fn name(&self) -> &str { "weather" }

    fn description(&self) -> String {
        "Get current weather for a location".to_string()
    }

    fn parameters(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates"
                }
            },
            "required": ["location"]
        })
    }

    async fn call(&self, call: ToolCall) -> Result<Value> {
        let location = call.params.get("location")
            .and_then(|v| v.as_str())
            .ok_or_else(|| Error::Tool("Missing 'location' parameter".into()))?;

        Ok(json!({
            "location": location,
            "temperature": 22,
            "unit": "celsius"
        }))
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut registry = ToolRegistry::new();
    registry.register(Box::new(WeatherTool)).unwrap();

    let call = ToolCall::new("weather", json!({"location": "London"}), "call-1");
    let response = registry.call(call).await?;
    println!("Result: {:?}", response.result);

    Ok(())
}
```

### Memory Management

```rust
use agentkit::domain::memory::{
    MemoryEntry, MemoryRole, ShortTermMemory, MemoryStore, InMemoryStore, LongTermMemory,
};

// Short-term memory (bounded ring buffer)
let mut short_term = ShortTermMemory::new(5);
short_term.add(MemoryEntry::user("What is Rust?"));
short_term.add(MemoryEntry::assistant("Rust is a systems programming language..."));
short_term.add(MemoryEntry::user("Tell me more"));
// Oldest entry auto-evicted when limit reached

println!("Memory entries: {}", short_term.len());

// Long-term memory (persistent store)
let store = InMemoryStore::new();
let mut long_term = LongTermMemory::new(store);
long_term.add(MemoryEntry::user("Key fact: Rust has no GC")).unwrap();

let results = long_term.search("Rust", 10).unwrap();
println!("Found {} memories", results.len());
```

### Custom Memory Store

Implement `MemoryStore` for any backend:

```rust
use agentkit::domain::memory::{MemoryEntry, MemoryStore};

struct FileStore {
    path: std::path::PathBuf,
}

impl MemoryStore for FileStore {
    fn save(&mut self, entry: &MemoryEntry) -> Result<(), String> {
        // Append entry to file
        Ok(())
    }

    fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, String> {
        // Search file contents
        Ok(vec![])
    }

    fn clear(&mut self) -> Result<(), String> {
        // Truncate file
        Ok(())
    }
}
```

### Using the Prelude

The `prelude` module re-exports the most commonly used types:

```rust
use agentkit::prelude::*;

// Available: Agent, AgentConfig, AgentState, ExecutionStep,
//            Skill, SkillResult, SkillRegistry,
//            Tool, ToolCall, ToolResponse, ToolRegistry,
//            MemoryEntry, MemoryStore, ShortTermMemory,
//            Context, Output, AgentExecutor
```

## Built-in Implementations

| Type | Name | Description |
|------|------|-------------|
| Skill | `WebSearchSkill` | Placeholder web search skill |
| Tool | `CalculatorTool` | Placeholder math expression evaluator |
| MemoryStore | `InMemoryStore` | In-memory store for testing |
| Agent | `SimpleAgent` | Echo agent (returns input prefixed with "Echo:") |

## Development

```bash
# Build
cargo build

# Run tests
cargo test

# Format
cargo fmt

# Lint
cargo clippy

# Run binary
cargo run --bin agentkit
```

## License

MIT OR Apache-2.0
