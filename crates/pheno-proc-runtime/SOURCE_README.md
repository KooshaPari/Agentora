> **Pinned references (Phenotype-org)**
> - MSRV: see rust-toolchain.toml
> - cargo-deny config: see deny.toml
> - cargo-audit: rustsec/audit-check@v2 weekly
> - Branch protection: 1 reviewer required, no force-push
> - Authority: phenotype-org-governance/SUPERSEDED.md

# PhenoProc

**Status:** maintenance

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/KooshaPari/PhenoProc/actions/workflows/ci.yml/badge.svg)](https://github.com/KooshaPari/PhenoProc/actions/workflows/ci.yml)
[![Rust](https://img.shields.io/badge/rust-1.75%2B-orange.svg)](https://www.rust-lang.org)

High-performance process orchestration and lifecycle management library for Rust. Provides unified APIs for process pooling, task queuing, shared memory coordination, and inter-process communication (IPC) via Unix domain sockets.

## Overview

**PhenoProc** is the central process management and workflow orchestration layer enabling reliable, efficient process execution across the Phenotype ecosystem. It handles process pooling, command deduplication, priority-based task queuing, and advanced IPC patterns needed for complex multi-process architectures.

**Core Mission**: Simplify process lifecycle management and inter-process coordination, reducing operational complexity while maintaining safety and performance guarantees.

## Technology Stack

- **Language**: Rust (Edition 2024)
- **Concurrency**: Tokio async runtime
- **IPC Mechanisms**:
  - Unix Domain Sockets (UDS) for local IPC
  - Shared Memory (SHM) for zero-copy data sharing
  - Message passing with priority queues
- **Key Crates**:
  - `pheno-proc-core` — Process pool, lifecycle management, ManagedProcess primitives
  - `pheno-proc-dedup` — Command deduplication and memoization
  - `pheno-proc-queue` — Priority task queue with Tokio integration
  - `pheno-proc-shm` — Shared memory management and synchronization
  - `pheno-proc-uds` — Unix domain socket communication patterns

## Key Features

- **Process Pooling**: Reusable worker pools with configurable concurrency and recycling policies
- **Lifecycle Management**: Automatic cleanup, graceful shutdown, and error recovery
- **Task Deduplication**: Prevent redundant process execution with intelligent memoization
- **Priority Queuing**: Task scheduling with priority levels and dynamic load balancing
- **Shared Memory**: Zero-copy IPC via POSIX shared memory with proper synchronization
- **Unix Sockets**: Non-blocking IPC for local service communication and multiplexing
- **Async-First**: Full Tokio integration for high-concurrency workloads

## Quick Start

```bash
# Clone and explore
git clone <repo-url>
cd PhenoProc

# Review governance and architecture
cat CLAUDE.md          # Project governance
cat SPEC.md            # Comprehensive specification
cat AGENTS.md          # Agent operating contract

# Build and test all crates
cargo build --release
cargo test --workspace
cargo clippy --workspace -- -D warnings

# View online documentation
npm install -g vitepress  # if not installed
cd docs && npm install && npm run docs:dev
```

## Project Structure

```
PhenoProc/
├── crates/
│   ├── pheno-proc-core/       # Core process management
│   ├── pheno-proc-dedup/      # Command deduplication
│   ├── pheno-proc-queue/      # Priority task queue
│   ├── pheno-proc-shm/        # Shared memory coordination
│   └── pheno-proc-uds/        # Unix domain socket patterns
├── docs/                      # VitePress documentation
├── examples/                  # Integration examples
└── SPEC.md, CLAUDE.md, AGENTS.md
```

## Use Cases

| Pattern | Crate | Example |
|---------|-------|---------|
| Worker pools | proc-core | Multi-process workload distribution |
| Memoization | proc-dedup | Skip redundant long-running tasks |
| Task scheduling | proc-queue | Priority-based job execution |
| Data sharing | proc-shm | Zero-copy buffer exchange |
| Service comm. | proc-uds | Local IPC between services |

## Related Phenotype Projects

- **[AgilePlus](../AgilePlus)** — Task/work scheduling via PhenoProc queues
- **[PhenoPlugins](../PhenoPlugins)** — Plugin lifecycle management using process primitives
- **[Tracera](../Tracera)** — Distributed tracing integration with proc monitoring

## Sub-Projects & Modules

This monorepo contains tightly integrated sub-projects for specialized process concerns:

- **phenotype-validation/** — Schema validation and rule evaluation for process inputs/outputs
- **phenotype-router-monitor/** — Request routing with circuit breaker patterns and latency instrumentation
- **phenotype-colab-extensions/** — Event-driven inter-service coordination via event sourcing and replay
- **phenotype-config-ts/** — Type-safe configuration bindings for TypeScript/JavaScript consumers
- **phenotype-cli-core/** — Standard CLI utilities for process spawning and signal handling
- **python/** — Python interoperability layer and bindings

## License

MIT — see [LICENSE](./LICENSE).

## Governance

Governance, contribution guidelines, and agent operating contract in `CLAUDE.md` and `AGENTS.md`. Functional requirements and FR-to-test traceability in `docs/FUNCTIONAL_REQUIREMENTS.md`.