# PhenoAgent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Quality Gate](https://github.com/KooshaPari/PhenoAgent/actions/workflows/quality-gate.yml/badge.svg)](https://github.com/KooshaPari/PhenoAgent/actions/workflows/quality-gate.yml)
[![Rust](https://img.shields.io/badge/rust-1.75%2B-orange.svg)](https://www.rust-lang.org)
[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net)

Distributed agent orchestration framework with plugin architecture, skill system, and multi-model routing for autonomous agentic workflows across the Phenotype ecosystem.

## Overview

PhenoAgent provides a unified framework for building autonomous agents with composable skills, multi-model inference routing, and coordination primitives. It integrates with external tool providers (MCP, Composio, E2B), manages agent state and memory, and orchestrates multi-agent workflows with clear contract boundaries between agent components.

## Technology Stack

- **Core**: Rust (agent daemon, policy enforcement), Go (CLI, API gateway)
- **IPC**: gRPC + Protocol Buffers for agent-daemon communication
- **Skills**: Skill registry with MCP-compatible tool adapters
- **Models**: Multi-model routing (Claude, GPT-4, Gemini, local LLMs via Ollama)
- **Storage**: Event-sourced agent state (SQLite backend)
- **Async Runtime**: Tokio (Rust), Go concurrency primitives

## Key Features

- **Skill System**: Pluggable skill registry with tool discovery, versioning, and auto-routing
- **Multi-Model Inference**: Transparent model routing with fallback policies
- **Plugin Architecture**: Extensible tool providers (MCP, Composio, E2B, custom integrations)
- **Agent Daemon**: Background orchestration with state persistence and event sourcing
- **CLI Interface**: `pheno-cli` for agent operations (create, run, monitor, debug)
- **Workflow Coordination**: Multi-agent job scheduling and dependency resolution
- **Observability**: Structured logging, distributed tracing, agent telemetry
- **Contract Enforcement**: Type-safe skill contracts with schema validation

## Quick Start

```bash
# Clone the repository
git clone https://github.com/KooshaPari/PhenoAgent.git
cd PhenoAgent

# Review governance and project spec
cat CLAUDE.md
cat PRD.md

# Build the agent daemon and CLI
cargo build --release -p phenotype-daemon
cargo build --release -p pheno-cli

# Start the agent daemon
./target/release/phenotype-daemon --config config.toml

# Create and run an agent
./target/release/pheno-cli agent create --name my-agent --model claude-opus-4-1
./target/release/pheno-cli agent run --name my-agent --task "analyze code in repo"

# List available skills
./target/release/pheno-cli skill list

# Monitor agent execution
./target/release/pheno-cli agent logs --name my-agent --follow
```

## Project Structure

```
PhenoAgent/
├── Cargo.toml                    # Rust workspace manifest
├── phenotype-daemon/             # Agent orchestration daemon
│   ├── src/
│   │   ├── agent/               # Agent lifecycle, state machine
│   │   ├── skill/               # Skill registry, routing
│   │   ├── model/               # Model provider abstractions
│   │   └── workflow/            # Multi-agent coordination
│   └── Cargo.toml
├── pheno-cli/                    # Command-line interface
│   ├── src/
│   │   ├── commands/            # CLI command handlers
│   │   ├── config/              # Config loading and validation
│   │   └── main.rs              # CLI entry point
│   └── Cargo.toml
├── phenotype-agent-core/         # Core types and traits
│   ├── src/
│   │   ├── agent.rs             # Agent trait definitions
│   │   ├── skill.rs             # Skill types and contracts
│   │   ├── model.rs             # Model provider interfaces
│   │   └── error.rs             # Error types
│   └── Cargo.toml
├── agentapi/                     # gRPC API definitions
│   └── proto/                    # Protocol Buffer schemas
├── CLIProxyAPI/                  # CLI proxy/gateway
│   └── src/
├── docs/                         # Architecture docs, design decisions
│   ├── adr/                     # Architecture Decision Records
│   └── guides/                  # Integration guides
├── tests/                        # Integration and e2e tests
└── worklogs/                     # Work tracking (AgilePlus)
```

## Related Phenotype Projects

- **[thegent-dispatch](../thegent-dispatch/)** — Agent execution orchestration and task scheduling
- **[agentapi-plusplus](../agentapi-plusplus/)** — Multi-model AI gateway with fallback routing
- **[cheap-llm-mcp](../cheap-llm-mcp/)** — Cost-optimized model routing and batch processing
- **[PhenoMCP](../PhenoMCP/)** — MCP server collection for skill discovery and integration

## Governance & Contributing

- **CLAUDE.md** — Project conventions, workspace setup
- **PRD.md** — Product requirements and vision
- **ADR.md** — Architecture decisions and patterns
- **PLAN.md** — Implementation roadmap
- **AGENTS.md** — CI/CD, quality gates, testing requirements

For testing, spec traceability, and contribution guidelines, see [AGENTS.md](AGENTS.md).

## Development

```bash
# Install dependencies
cargo build --workspace

# Run all tests
cargo test --workspace -- --nocapture

# Lint and format
cargo clippy --workspace -- -D warnings
cargo fmt --check

# Generate API client code
./scripts/gen-proto.sh

# Run daemon locally (requires config)
cargo run -p phenotype-daemon -- --config local.toml
```

## License

Proprietary — Phenotype Ecosystem. Internal use only.

## License

MIT — see [LICENSE](./LICENSE).
