# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `[lints.rust]` table in `Cargo.toml` with `unsafe_code = "forbid"` (centralised lint policy, SOTA Rust 1.74+ pattern).
- MCP domain ports `ServerPort` and `ResourcePort` (plus `McpTool`, `McpResource`, `McpToolRequest`, `McpToolResponse` data types) in `crate::domain::ports`, formalising the AgentMCP → Agentora integration path (#86, ADR-017).
- `docs/mcp/INTEGRATION.md` documenting the McpKit `python/agentmcp/` → Agentora migration: source-to-target port map, hexagonal placement, port contracts, and consumer migration checklist.

### Changed

- Pinned `rust-toolchain.toml` channel from `stable` to `1.95.0` for reproducible builds (MSRV remains 1.75).
- `README.md` / `AGENTS.md` / `CLAUDE.md` feature-flag tables updated to reflect current `reqwest 0.13` / `redis 1.2` / `rusqlite 0.40` versions from `Cargo.toml`.

### Fixed

- `cargo fmt --check` was failing across 10 files (import-group ordering, module-declaration sort, long-line wrapping). Re-formatted; CI gate now passes.

[Unreleased]: https://github.com/KooshaPari/Agentora/compare/main...HEAD
