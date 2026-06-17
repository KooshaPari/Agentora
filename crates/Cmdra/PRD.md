# agentkit — Product Requirements Document

## Executive Summary

**agentkit** is a universal CLI framework library for Rust, providing reusable building blocks for building robust, extensible command-line applications. It implements hexagonal (ports-and-adapters) architecture so application authors can wire domain logic to CLI parsing, config loading, logging, and plugin systems without coupling to any specific infrastructure.

### Product Vision

Provide the single Rust library that any Phenotype-ecosystem CLI tool reaches for first: a clean, well-layered set of domain types, ports, application services, and adapters covering the 80% of CLI infrastructure every tool needs — so authors focus on domain logic, not framework plumbing.

---

## User Personas

### Persona 1: CLI Tool Author (Phenotype Org)
- **Goal**: Build a new CLI tool (e.g., `phenotype-cli-core`, `hexkit`) with clean architecture from day one
- **Use Case**: Add `agentkit` as a dependency, define `Command` / `Argument` / `Option` domain objects, register handlers, wire to `CliAdapter`
- **Key Needs**: Compile-time type safety, zero-cost abstractions, easy plugin registration, minimal boilerplate

### Persona 2: Plugin Author
- **Goal**: Extend an agentkit-based CLI with custom commands without modifying the host binary
- **Use Case**: Compile a shared library (`.so`/`.dll`/`.dylib`) implementing `Plugin` trait; place in plugin directory; host discovers and loads it at startup
- **Key Needs**: Stable plugin ABI, clear `Plugin` trait contract, semver-compatible versioning

### Persona 3: Framework Evaluator
- **Goal**: Compare agentkit against clap/xtask/cargo-xtask as a CLI foundation
- **Use Case**: Review architecture, run benchmarks, inspect test coverage
- **Key Needs**: Clean documentation, property-based tests, criterion benchmarks, clear layer separation

---

## Epics and User Stories

### E1: Domain Modeling

**E1.1** As a CLI tool author, I want to define commands using composable `Command` builder so I can describe the command tree without coupling to a specific parser.

**E1.2** As a CLI tool author, I want typed `Argument`, `CliOption`, and `Flag` value objects so argument parsing is validated before my handler runs.

**E1.3** As a CLI tool author, I want a `Context` value object that carries parsed input so my handlers are pure functions of context.

**E1.4** As a CLI tool author, I want a typed `Output` / `Result` pair so handler return types are consistent across the framework.

### E2: Application Layer

**E2.1** As a CLI tool author, I want a `CommandHandler` trait with async `handle(&Context) -> Result<Output>` so handlers are independently testable.

**E2.2** As a CLI tool author, I want a `DefaultHandler<F>` wrapper so I can register closures as handlers without boilerplate structs.

**E2.3** As a CLI tool author, I want a `CommandExecutor` that maps command names to handlers and dispatches invocations so I don't write dispatch logic.

**E2.4** As a CLI tool author, I want query handlers (`QueryHandler` trait) separate from command handlers so read-only operations are distinguishable.

### E3: Adapters — Primary (CLI Parsing)

**E3.1** As a CLI tool author, I want a `CliAdapter` built on `clap` that translates `Vec<String>` args into a `Context` so I can test parsing independently.

**E3.2** As a CLI tool author, I want auto-generated help text from `Command` metadata so I don't maintain help strings separately.

**E3.3** As a CLI tool author, I want shell completion generation from `Command` metadata for bash/zsh/fish.

### E4: Adapters — Secondary (Config, Logging, Persistence)

**E4.1** As a CLI tool author, I want a `ConfigLoader` port with TOML and YAML implementations so config format is swappable.

**E4.2** As a CLI tool author, I want a `Logger` port backed by `tracing` + `tracing-subscriber` so structured log output is configurable at runtime.

**E4.3** As a CLI tool author, I want a `Persistence` port with a filesystem key-value implementation so tools can store state between invocations.

### E5: Plugin System

**E5.1** As a plugin author, I want a `Plugin` trait with `name()`, `version()`, `init()`, `commands()`, and `cleanup()` so I know exactly what to implement.

**E5.2** As a plugin author, I want `PluginManager::load_from_dir(path)` to scan a directory and load all valid shared libraries so discovery is automatic.

**E5.3** As a CLI tool author, I want `PluginManager` to merge plugin-provided `Command` objects into the main command tree so plugin commands appear in help and dispatch.

**E5.4** As a plugin author, I want `semver` version checks on load so incompatible plugins fail loudly rather than silently misbehaving.

### E6: Observability

**E6.1** As a CLI tool author, I want a `Telemetry` port with `record_execution`, `record_error`, and `record_metric` so I can emit structured metrics without choosing a backend.

**E6.2** As a CLI tool author, I want tracing spans around command dispatch so distributed traces propagate through multi-step workflows.

---

## Acceptance Criteria

| Story | Acceptance Criterion |
|-------|---------------------|
| E1.1 | `Command::new("foo").subcommand(...)` compiles and produces a valid tree |
| E2.1 | `DefaultHandler::new(closure)` satisfies `CommandHandler` trait |
| E2.3 | `CommandExecutor::get_command("unknown")` returns `None` without panic |
| E3.1 | `CliAdapter::parse(args)` returns typed `Context` for valid args; `Err` for invalid |
| E5.2 | `PluginManager::load_from_dir` loads `.so`/`.dll`/`.dylib` files; skips non-library files |
| E5.4 | Plugin with semver-incompatible version returns `DomainError::PluginError` |

---

## Out of Scope (v0.1)

- Built-in TUI (terminal UI) components — use a separate TUI library
- Network-aware commands (HTTP clients, gRPC) — agentkit is infrastructure-agnostic
- Windows-specific installer or MSI packaging
- Hot-reload of plugins at runtime (load/unload only at startup)
