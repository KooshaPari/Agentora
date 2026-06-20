# Agentora - Specification

## Problem

`Agentora` addresses a specific need in the Phenotype fleet: hexagonal-architecture framework for ai agents with skill system, tool registry, two-tier memory. Without a canonical implementation, downstream consumers must reinvent the same primitives, leading to fragmentation and divergent behavior across the fleet.

## Solution

`Agentora` provides a single, well-tested, well-documented implementation of this capability. The package ships with:
- A stable public API
- A test matrix (unit + integration; e2e + perf where applicable)
- Observability hooks (info-level tracing via pheno-tracing where applicable)
- CI gates (lint, format, test, security audit per ADR-042)

## Architecture

- Language: python
- Tier: 1 (0=foundational, 1=core, 2=extension, 3=experimental)
- Maturity: stable
- Layout: standard layout per language conventions
- Hexagonal: ports in `port/`, adapters in `adapter/` (where applicable)
- Versioning: SemVer
- License: MIT or Apache-2.0 (per repo)

## API

See `README.md` for the user-facing API. Internal modules are documented via rustdoc / pydoc / godoc / TypeDoc. Example usage in `examples/`.

## Status

- Current tier: 1
- Maturity: stable
- Coverage: see `llms.txt`
- Security: see `SECURITY.md` and `.github/workflows/security.yml`
- Registry entry: KooshaPari/phenotype-registry/registry/components.lock
- Maintainer: @KooshaPari
