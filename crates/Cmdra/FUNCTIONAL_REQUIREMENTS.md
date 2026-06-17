# agentkit — Functional Requirements

## FR-DOM-001: Command Entity

| Requirement ID | Description | Verification |
|---|---|---|
| FR-DOM-001.1 | System SHALL provide a `Command` struct with fields: `name: String`, `description: String`, `version: Option<String>`, `subcommands: Vec<Command>`, `arguments: Vec<Argument>`, `options: Vec<CliOption>`, `flags: Vec<Flag>` | Unit test: construct `Command` with all fields; assert field values |
| FR-DOM-001.2 | `Command::new(name)` SHALL return a `Command` with empty subcommand/argument/option/flag collections | Unit test: `Command::new("test")` — all Vec fields are empty |
| FR-DOM-001.3 | Builder methods (`description`, `version`, `subcommand`, `argument`, `option`, `flag`) SHALL return `Self` to enable chaining | Unit test: chained builder compiles and produces expected struct |
| FR-DOM-001.4 | `Command` SHALL implement `Debug`, `Clone`, `PartialEq`, `Eq` | Unit test: assert `cmd1 == cmd1.clone()` |

---

## FR-DOM-002: Argument and Option Value Objects

| Requirement ID | Description | Verification |
|---|---|---|
| FR-DOM-002.1 | `Argument` SHALL have fields: `name`, `description`, `required: bool`, `default_value: Option<String>`, `multiple: bool` | Unit test: construct `Argument` with all fields |
| FR-DOM-002.2 | `CliOption` SHALL have fields: `name`, `short: Option<char>`, `description`, `required: bool`, `default_value: Option<String>`, `value_type: OptionValueType` | Unit test: construct `CliOption` with short flag |
| FR-DOM-002.3 | `Flag` SHALL have fields: `name`, `short: Option<char>`, `description` | Unit test: construct `Flag` |
| FR-DOM-002.4 | All value object types SHALL implement `Debug`, `Clone`, `PartialEq`, `Eq` | Unit test: clone equality |

---

## FR-DOM-003: Context and Input/Output Value Objects

| Requirement ID | Description | Verification |
|---|---|---|
| FR-DOM-003.1 | `Context` SHALL carry: parsed `Input`, `command_name: String`, environment metadata | Unit test: `Context` fields accessible |
| FR-DOM-003.2 | `Input` SHALL support `get_arg(name) -> Option<&str>`, `get_option(name) -> Option<&str>`, `has_flag(name) -> bool` | Unit test: input constructed with known values; accessors return expected |
| FR-DOM-003.3 | `Output` SHALL support text content and optional structured data (`serde_json::Value`) | Unit test: `Output::text("hello")` produces non-empty output |
| FR-DOM-003.4 | Domain `Result<T>` SHALL be `Result<T, DomainError>` where `DomainError` uses `thiserror` | Unit test: `DomainError::PluginError("msg".into())` displays expected string |

---

## FR-DOM-004: Domain Ports (Interfaces)

| Requirement ID | Description | Verification |
|---|---|---|
| FR-DOM-004.1 | `CommandHandler` trait SHALL define `async fn handle(&self, ctx: &Context) -> Result<Output>` and `fn validate(&self, input: &Input) -> Result<()>` (with default `Ok(())`) | Unit test: mock `CommandHandler` satisfies trait bounds |
| FR-DOM-004.2 | `CommandExecutor` trait SHALL define `async fn execute(&self, command: &Command, input: Input) -> Result<Output>` | Unit test: mock satisfies trait bounds |
| FR-DOM-004.3 | `ConfigLoader` trait SHALL define `fn load() -> Result<serde_json::Value>` and `fn get(key: &str) -> Result<Option<serde_json::Value>>` | Unit test: `TomlConfigLoader` implements `ConfigLoader` |
| FR-DOM-004.4 | `OutputFormatter` trait SHALL define `fn format(&self, output: Output) -> String` | Unit test: `JsonFormatter` returns valid JSON string |
| FR-DOM-004.5 | `Logger` trait SHALL define `info`, `debug`, `warn`, `error` methods taking `&str` | Unit test: `TracingLogger` implements `Logger` |
| FR-DOM-004.6 | `Plugin` trait SHALL define `name() -> &str`, `version() -> &str`, `init() -> Result<()>`, `commands() -> Vec<Command>`, `cleanup() -> Result<()>` | Unit test: test struct satisfies `Plugin` |
| FR-DOM-004.7 | `Telemetry` trait SHALL define `record_execution(command, duration_ms, success)`, `record_error(command, error)`, `record_metric(name, value)` | Unit test: no-op telemetry satisfies trait |
| FR-DOM-004.8 | `Persistence` trait SHALL define `save(key, &[u8])`, `load(key) -> Result<Option<Vec<u8>>>`, `delete(key)` | Unit test: `FilePersistence` round-trips a byte slice |

---

## FR-APP-005: Application Command Handling

| Requirement ID | Description | Verification |
|---|---|---|
| FR-APP-005.1 | `DefaultHandler<F, Fut>` SHALL wrap an async closure satisfying `Fn(&Context) -> Fut` and implement `CommandHandler` | Unit test: closure handler handles a `Context` and returns `Ok(output)` |
| FR-APP-005.2 | `CommandExecutor` (application struct) SHALL maintain a `Vec<Command>` registry; `register(Command) -> Self` SHALL append to the registry | Unit test: register 3 commands; `list_commands()` returns 3 |
| FR-APP-005.3 | `CommandExecutor::get_command(name)` SHALL return `Some(&Command)` for registered names and `None` for unknown names | Unit test: two cases |
| FR-APP-005.4 | Application services SHALL be `Send + Sync` to support async multi-threaded runtimes | Compile test: assert `DefaultHandler<F, Fut>: Send + Sync` where `F: Send + Sync` |

---

## FR-APP-006: Query Handling

| Requirement ID | Description | Verification |
|---|---|---|
| FR-APP-006.1 | `QueryHandler` trait SHALL define `async fn handle(&self, ctx: &Context) -> Result<Output>` separate from `CommandHandler` | Unit test: distinct trait impls compile without conflict |
| FR-APP-006.2 | Query handlers SHALL be registrable in `CommandExecutor` alongside command handlers | Unit test: register both types; both dispatch correctly |

---

## FR-ADAPT-007: CLI Adapter (Primary)

| Requirement ID | Description | Verification |
|---|---|---|
| FR-ADAPT-007.1 | `CliAdapter` SHALL use `clap` to parse `Vec<String>` args into a typed `Input` | Unit test: `parse(vec!["cmd", "--opt", "val"])` returns `Input` with option `opt = "val"` |
| FR-ADAPT-007.2 | `CliAdapter` SHALL generate help text from `Command` metadata; `--help` flag SHALL print generated help and exit 0 | Integration test: run binary with `--help`; exit code 0; stdout contains command name |
| FR-ADAPT-007.3 | `CliAdapter` SHALL return `Err(DomainError)` for unrecognized arguments | Unit test: unknown flag returns error variant |
| FR-ADAPT-007.4 | `CliParser` port SHALL be satisfied by `CliAdapter` | Compile test: `CliAdapter: CliParser` |

---

## FR-ADAPT-008: Config Adapter (Secondary)

| Requirement ID | Description | Verification |
|---|---|---|
| FR-ADAPT-008.1 | `TomlConfigLoader` SHALL implement `ConfigLoader` by parsing TOML files via the `toml` crate (`toml = "0.8"`) | Unit test: parse fixture TOML file; `get("key")` returns expected value |
| FR-ADAPT-008.2 | `YamlConfigLoader` SHALL implement `ConfigLoader` by parsing YAML files via `yaml-rust2` | Unit test: parse fixture YAML file; `get("key")` returns expected value |
| FR-ADAPT-008.3 | `ConfigLoader::load()` SHALL return `Err` if the file does not exist | Unit test: load nonexistent path returns `Err` |

---

## FR-ADAPT-009: Logging Adapter (Secondary)

| Requirement ID | Description | Verification |
|---|---|---|
| FR-ADAPT-009.1 | `TracingLogger` SHALL implement `Logger` using `tracing` macros (`tracing = "0.1"`) | Unit test: `TracingLogger` calls do not panic; trait satisfied |
| FR-ADAPT-009.2 | Log verbosity SHALL be configurable via `RUST_LOG` env var through `tracing-subscriber` with `EnvFilter` | Integration test: set `RUST_LOG=debug`; debug messages appear in output |
| FR-ADAPT-009.3 | Log output SHALL support appending to files via `tracing-appender` | Integration test: configure file appender; log lines appear in file |

---

## FR-PLUGIN-010: Plugin System

| Requirement ID | Description | Verification |
|---|---|---|
| FR-PLUGIN-010.1 | `PluginManager::load_from_dir(path)` SHALL scan directory for `.so` (Linux), `.dll` (Windows), `.dylib` (macOS) files and attempt to load each | Unit test (with mock lib): returns list of loaded plugin names |
| FR-PLUGIN-010.2 | `PluginManager::load_plugin(path)` SHALL use `libloading::Library` to load the shared library and call a `create_plugin` symbol of type `fn() -> Box<dyn Plugin>` | Unit test: mock shared lib returns expected plugin name |
| FR-PLUGIN-010.3 | Plugin load SHALL fail with `DomainError::PluginError` if the directory does not exist | Unit test: nonexistent dir returns `Err` |
| FR-PLUGIN-010.4 | Plugin load SHALL fail with `DomainError::PluginError` if the shared library does not export `create_plugin` | Unit test: lib without symbol returns `Err` |
| FR-PLUGIN-010.5 | `PluginManager` SHALL call `plugin.init()` on load and `plugin.cleanup()` on unload; errors in either SHALL propagate as `DomainError::PluginError` | Unit test: plugin whose `init()` returns `Err` causes load to fail |
| FR-PLUGIN-010.6 | Commands returned by `plugin.commands()` SHALL be mergeable into the host `CommandExecutor` registry | Unit test: register plugin commands; `get_command(plugin_cmd_name)` returns `Some` |

---

## FR-OBS-011: Telemetry and Tracing

| Requirement ID | Description | Verification |
|---|---|---|
| FR-OBS-011.1 | `Telemetry::record_execution` SHALL accept command name, duration in ms, and success bool | Unit test: no-op impl satisfies trait signature |
| FR-OBS-011.2 | `tracing` spans SHALL be emitted around command dispatch in `CommandExecutor` | Unit test with `tracing-test`: span `command.execute` appears in collected spans |
| FR-OBS-011.3 | `uuid::Uuid::new_v4()` SHALL be used for execution trace IDs | Unit test: generated IDs are unique across 1000 calls |

---

## FR-QUAL-012: Build and Quality Gates

| Requirement ID | Description | Verification |
|---|---|---|
| FR-QUAL-012.1 | `cargo clippy --workspace --all-targets -- -D warnings` SHALL emit zero warnings | CI: clippy job passes |
| FR-QUAL-012.2 | `cargo fmt --all -- --check` SHALL pass | CI: fmt check passes |
| FR-QUAL-012.3 | `cargo test --workspace` SHALL pass all unit tests | CI: test job passes |
| FR-QUAL-012.4 | Property-based tests using `proptest = "1.0"` SHALL cover `Command` entity construction | Test file: at least one `proptest!` block for `Command` builder |
| FR-QUAL-012.5 | Benchmarks using `criterion = "0.5"` SHALL cover command dispatch throughput | Bench file: at least one `criterion_group!` for dispatch |
