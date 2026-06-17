## Summary
Add the next `clikit` migration slice by wiring configuration loading, tracing-backed logging, and command help plumbing into the application layer.

## Context
This continues the staged migration from `phenotype-cli-core` into `clikit`. The previous slice covered deterministic argv parsing; this slice expands the runtime support needed for command discovery, help output, configuration access, and structured logging.

## Changes
- Added `from_str` helpers to JSON and TOML config loaders for testable configuration loading
- Added command registry helpers and help rendering on `CommandExecutor`
- Expanded `CliApplication` with context/config hydration and help lookup helpers
- Wired tracing initialization into logging and tracing infrastructure
- Re-exported the new infrastructure helpers from the crate root

## Testing
- `cargo test -q`

## Links
- Migration plan: `plans/migrate-phenotype-cli-core-to-clikit.md`
- Prior slice PR: https://github.com/KooshaPari/clikit/pull/1