# PhenoAgent — CLAUDE.md

Phenotype agent core, daemon, and CLI — extracted from phenotype-infra.

## Governance

- **Specs:** See ADR.md, PLAN.md, FUNCTIONAL_REQUIREMENTS.md
- **Agents:** AGENTS.md
- **Worklog:** worklog.md

## Project Structure

Multi-workspace Rust project:
- `phenotype-agent-core/` — Core agent runtime and traits
- `phenotype-daemon/` — Daemon process, socket management, lifecycle
- `agentapi/` — HTTP API gateway (Go; see CLIProxyAPI)
- `pheno-cli/` — CLI interface
- `docs/` — Architecture, runbooks, integration guides

## Local Quality Checks

From repo root:

```bash
cargo test --workspace
cargo clippy --workspace -- -D warnings
cargo fmt --check
```

## Work Requirements

1. Check for AgilePlus spec before implementing
2. Reference FUNCTIONAL_REQUIREMENTS.md for feature mapping
3. Update worklog.md with research/decisions
4. No code without corresponding spec entry

## Integration Notes

- Daemon uses Unix sockets (`/var/run/phenotype/agent.sock`)
- API routes defined in agentapi/ (Go; proxy pattern)
- CLI mirrors agentapi endpoints for interactive use
