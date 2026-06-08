# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `[lints.rust]` table in `Cargo.toml` with `unsafe_code = "forbid"` (centralised lint policy, SOTA Rust 1.74+ pattern).

### Changed

- Pinned `rust-toolchain.toml` channel from `stable` to `1.95.0` for reproducible builds (MSRV remains 1.75).
- `README.md` / `AGENTS.md` / `CLAUDE.md` feature-flag tables updated to reflect current `reqwest 0.13` / `redis 1.2` / `rusqlite 0.40` versions from `Cargo.toml`.

### Fixed

- `cargo fmt --check` was failing across 10 files (import-group ordering, module-declaration sort, long-line wrapping). Re-formatted; CI gate now passes.

[Unreleased]: https://github.com/KooshaPari/Agentora/compare/main...HEAD
