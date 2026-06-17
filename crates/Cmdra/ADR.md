# Architecture Decision Records — agentkit

## ADR-001: Hexagonal (Ports-and-Adapters) Architecture

**Status**: Accepted

**Context**: agentkit must be usable as a library by other CLI tools (phenotype-cli-core, hexkit, etc.) and must support testing without any external dependencies. The domain logic (command trees, argument parsing semantics, handler dispatch) should have zero coupling to clap, tracing, or any infrastructure crate.

**Decision**: Implement hexagonal architecture with four explicit layers:

```
src/
  domain/         # entities, value objects, ports (pure Rust, no external deps)
    entities/     # Command, Argument, CliOption, Flag
    value_objects/# Input, Output, Context
    ports/        # CommandHandler, ConfigLoader, Logger, Plugin, Telemetry, Persistence
    errors/       # DomainError (thiserror)
    events/       # domain events

  application/    # use cases, orchestration (depends on domain only)
    commands/     # DefaultHandler, CommandExecutor
    queries/      # QueryHandler implementations
    services/     # application-level services

  adapters/       # port implementations (depend on domain + application)
    primary/cli/  # CliAdapter (wraps clap)
    secondary/config/ # TomlConfigLoader, YamlConfigLoader
    secondary/logging/# TracingLogger

  infrastructure/ # cross-cutting (tracing-subscriber setup, error handling)
  plugins/        # PluginManager using libloading
```

`src/lib.rs` uses `__getattr__`-style re-exports to present a flat public API.

**Alternatives Considered**:
- Monolithic `src/lib.rs`: simpler for a small library but prevents independent testing of domain logic
- Layered architecture without explicit ports: ports make the dependency boundary explicit and enforce it via trait objects

**Consequences**:
- Positive: Domain types (`Command`, `Input`, `Output`) are unit-testable with zero dependencies
- Positive: Consumers can swap adapters (e.g., replace `CliAdapter` with an API adapter) without touching domain
- Negative: More files and indirection than a thin wrapper around clap
- Mitigation: `src/lib.rs` re-exports flatten the public API so consumers do not need to know internal paths

---

## ADR-002: clap v4 as the Primary CLI Parsing Adapter

**Status**: Accepted

**Context**: The primary adapter (`CliAdapter`) must translate `Vec<String>` into typed domain `Input`. Rust has several CLI parsing crates: clap, structopt (deprecated), pico-args, argh.

**Decision**: Use `clap = { version = "4.0", features = ["derive", "env"] }` as the sole CLI parsing dependency:
- `CliAdapter` wraps clap's `App`/`Command` API programmatically (not derive) to remain driven by domain `Command` objects
- `derive` feature enabled for internal use in agentkit's own binary (`src/bin/main.rs`)
- `env` feature enables `--option` values to fall back to env vars, which aligns with 12-factor CLI design

**Alternatives Considered**:
- pico-args: minimal but lacks help-generation from metadata; authors would write help strings manually
- structopt: deprecated in favor of clap v3/v4
- argh: Google's crate; derive-only, not programmable from runtime objects

**Consequences**:
- Positive: clap is the de facto standard; contributors know it; it generates high-quality help text and shell completions
- Positive: `env` feature allows env-var fallback without additional code in handlers
- Negative: clap is a non-trivial compile-time cost; adds ~10–20s to clean builds
- Mitigation: clap is the only primary-adapter dependency; domain compiles independently

---

## ADR-003: Dynamic Plugin Loading via libloading

**Status**: Accepted

**Context**: agentkit needs a runtime plugin system so tool authors can extend their CLI without recompiling the host binary. The plugin must provide a stable ABI boundary.

**Decision**: Use `libloading = "0.8"` for platform-native shared library loading:
- Plugins are `.so` (Linux) / `.dylib` (macOS) / `.dll` (Windows) shared libraries
- Each plugin exports a `create_plugin` C-ABI function: `extern "C" fn create_plugin() -> Box<dyn Plugin>`
- `PluginManager::load_plugin(path)` calls `Library::new(path)` then resolves the `create_plugin` symbol
- Plugin directories are scanned by extension (`.so`, `.dll`, `.dylib`) via `std::fs::read_dir`
- `semver = "1.0"` is used for version compatibility checks between host and plugin

**Alternatives Considered**:
- Compile-time plugins via Cargo features: simpler but requires recompilation for every extension
- Extism / WASM plugins: safer (sandbox), but requires WASM runtime and complicates plugin authorship
- `dlopen2` crate: similar to libloading with minor API differences; libloading has more downloads and longer track record

**Consequences**:
- Positive: Plugins can be authored independently and distributed as binary artifacts
- Positive: `PluginManager` can load/unload without process restart
- Negative: `unsafe` code is required at the `Library::new` call; plugin ABIs can be fragile across Rust compiler versions
- Negative: Dynamic linking is not supported on all targets (e.g., some embedded, WASI)
- Mitigation: `Plugin` trait is kept minimal; `init()`/`cleanup()` lifecycle hooks catch mis-initialized plugins; semver check rejects version mismatches loudly

---

## ADR-004: thiserror for Domain Error Types

**Status**: Accepted

**Context**: Domain errors must be descriptive, composable, and carry context without depending on `anyhow` (which erases type information). Application and adapter layers use `anyhow` for ergonomic error propagation.

**Decision**: Domain layer uses `thiserror = "1.0"` exclusively:
- `DomainError` enum with variants: `PluginError(String)`, `ParseError(String)`, `ConfigError(String)`, `IoError(#[from] std::io::Error)`, and others
- All domain ports return `Result<T, DomainError>`
- Adapter and infrastructure layers wrap `DomainError` into `anyhow::Error` at their boundary

**Alternatives Considered**:
- `anyhow` throughout: ergonomic but loses type information; callers cannot match on error variants
- Manual `impl std::error::Error`: verbose; `thiserror` derives the same impl

**Consequences**:
- Positive: Domain callers can `match` on `DomainError` variants for precise error handling
- Positive: `#[from]` attribute in `thiserror` auto-generates `From<std::io::Error>` conversions
- Negative: Adding new error variants is a breaking API change for consumers pattern-matching exhaustively
- Mitigation: `#[non_exhaustive]` attribute on `DomainError` prevents exhaustive matching outside the crate

---

## ADR-005: serde + TOML + YAML for Configuration Serialization

**Status**: Accepted

**Context**: CLI tools built on agentkit need to load configuration from files. TOML and YAML are the two most common formats in the Rust CLI ecosystem. Config types should be deserializable without depending on specific file-format crates in the domain.

**Decision**:
- `serde = { version = "1.0", features = ["derive"] }` in domain for `#[derive(Serialize, Deserialize)]` on config-carrying structs
- `toml = "0.8"` in the config adapter for TOML deserialization
- `yaml-rust2 = "0.8"` (actively maintained fork of `yaml-rust`) for YAML deserialization
- `ConfigLoader` port returns `serde_json::Value` as a universal intermediate representation; adapters deserialize into it

**Alternatives Considered**:
- `figment`: powerful multi-source config library; heavier than needed for a library (vs application)
- `config-rs`: similar; targets application-level config with layered sources; agentkit is a library so it exposes primitives, not policies
- JSON-only: many CLI users prefer TOML; JSON is too verbose for hand-written config

**Consequences**:
- Positive: `ConfigLoader` returns `serde_json::Value`, which is format-agnostic and serializable back to any format
- Positive: `yaml-rust2` is the maintained fork after the original `yaml-rust` was abandoned
- Negative: `serde_json::Value` as intermediate type loses schema information; callers must deserialize into typed structs themselves
- Mitigation: Provide helper `config_to<T: DeserializeOwned>(value: Value) -> Result<T>` utility in the adapter

---

## ADR-006: tracing + tracing-subscriber for Structured Logging and Observability

**Status**: Accepted

**Context**: CLI tools need structured logging. The Rust ecosystem has converged on the `tracing` facade. agentkit's `Logger` port should be implementable using `tracing` without forcing consumers to use it.

**Decision**:
- `tracing = "0.1"` in the `Logger` port implementation (`TracingLogger`) and for span instrumentation in `CommandExecutor`
- `tracing-subscriber = { version = "0.3", features = ["env-filter"] }` for subscriber setup (configured via `RUST_LOG`)
- `tracing-appender = "0.2"` for non-blocking file appending
- `Logger` port is in domain; `TracingLogger` adapter is in `adapters/secondary/logging/`

**Consequences**:
- Positive: `RUST_LOG=debug agentkit` enables debug output without recompilation
- Positive: Spans around command dispatch integrate with distributed tracing (OpenTelemetry-compatible subscribers)
- Negative: `tracing-subscriber` must be initialized once per process; multiple initializations panic
- Mitigation: Document that callers initialize the subscriber once in `main()`; agentkit itself does not call `tracing_subscriber::init()`

---

## ADR-007: async-trait for Async Port Definitions

**Status**: Accepted

**Context**: Rust's `async fn` in traits was unstable at project inception. `CommandHandler`, `CommandExecutor`, and environment-facing ports need to be async because I/O-bound operations (config loading, telemetry emission) are async in practice.

**Decision**: Use `async-trait = "0.1"` to annotate all async trait methods:
```rust
#[async_trait]
pub trait CommandHandler: Send + Sync {
    async fn handle(&self, ctx: &Context) -> Result<Output>;
}
```
All trait implementors are also annotated with `#[async_trait]`.

**Note**: Rust 1.75+ stabilized `async fn in trait` (AFIT) without `async-trait`. Migrate to AFIT when the project's MSRV (minimum supported Rust version) reaches 1.75.

**Consequences**:
- Positive: Async traits work on stable Rust today
- Negative: `async-trait` uses a `Box<dyn Future>` internally, adding an allocation per call
- Mitigation: For hot paths, provide synchronous fallback methods where allocation is unacceptable; document AFIT migration path

---

## ADR-008: proptest and criterion for Quality Assurance

**Status**: Accepted

**Context**: A CLI framework library is foundational infrastructure; regressions in entity construction or dispatch are high-impact. Property-based tests and benchmarks provide coverage that example-based tests miss.

**Decision**:
- `proptest = "1.0"` in `[dev-dependencies]` for property-based testing of `Command` entity invariants (e.g., cloned command equals original, builder methods are idempotent)
- `criterion = "0.5"` in `[dev-dependencies]` for benchmarking command dispatch throughput and plugin load times
- `tokio-test = "0.4"` for blocking-async test helpers in unit tests that need a runtime

**Consequences**:
- Positive: Proptest generates hundreds of random inputs; catches edge cases that hand-written tests miss
- Positive: Criterion produces statistically sound benchmarks with regression detection
- Negative: Proptest and Criterion increase test compile times
- Mitigation: Benchmark suite is in a separate `benches/` directory; not compiled during `cargo test`
