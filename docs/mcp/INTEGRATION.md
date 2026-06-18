# AgentMCP → Agentora Integration Path

**Issue:** #86
**ADR:** [ADR-017](#related) (AgentMCP remains the agent-runtime MCP lane)
**Source:** `KooshaPari/McpKit` · `python/agentmcp/` (merged at commit `0a46183`)
**Target:** `KooshaPari/Agentora` (this repo, crate `agentkit`)
**Status:** Ports defined; absorption in progress.

## Context

`McpKit/python/agentmcp/` was the prototype agent-runtime MCP lane. Per
ADR-017, **Agentora is the canonical owner** of agent-runtime MCP patterns
— not the retired `PhenoMCPServers/servers/` lane. The Python prototype
remains useful as a reference, but the production Rust ports now live in
`agentkit`'s domain layer.

This document is the migration guide for moving consumer code from the
McpKit AgentMCP patterns onto the canonical Agentora ports.

## Source → target map

| McpKit (`python/agentmcp/`) | Agentora (`agentkit`) | Notes |
|-----------------------------|----------------------|-------|
| `domain/models.py` (`McpTool`, `McpResource`, `Agent`) | `crate::domain::ports::{McpTool, McpResource}` | Pure-data descriptors, no IO. |
| `adapters/fastmcp.py` | `crate::adapters::mcp::fastmcp` *(planned)* | Implements `ServerPort`. |
| `adapters/cli.py` | `crate::adapters::mcp::cli` *(planned)* | Implements `ServerPort` (stdio transport). |
| `ports/server.py` | `crate::domain::ports::ServerPort` | Async trait, `Send + Sync`, `dyn`-safe. |
| `ports/resource.py` | `crate::domain::ports::ResourcePort` | Async trait, `Send + Sync`, `dyn`-safe. |

The McpKit source remains the reference implementation. The Rust port
mirrors the same surface but follows Agentora's hexagonal conventions
(domain owns traits, adapters implement them).

## Hexagonal placement

Per the layer rules in `AGENTS.md`:

```
  domain  ──▶  defines  ServerPort, ResourcePort  (no IO, no deps)
  ▲
  │ depends on
  │
  adapters  ──▶  implements ServerPort / ResourcePort
                  (fastmcp, cli, http, …)
  ▲
  │ depends on
  │
  application / infrastructure  ──▶  wires adapters into the agent runtime
```

The domain layer MUST NOT import anything from `adapters/` or
`infrastructure/`. Adding a new transport (e.g. WebSocket) is a pure
adapter change — no domain or application edits required.

## Port contracts

### `ServerPort`

```rust
#[async_trait]
pub trait ServerPort: Send + Sync {
    async fn start(&self) -> Result<()>;
    async fn stop(&self) -> Result<()>;
    async fn register_tool(&self, tool: McpTool) -> Result<()>;
    async fn list_tools(&self) -> Result<Vec<McpTool>>;
    async fn call_tool(&self, req: McpToolRequest) -> Result<McpToolResponse>;
}
```

Lifecycles are owned by the implementer. `start` MUST be idempotent;
`stop` MUST be safe to call when not started.

### `ResourcePort`

```rust
#[async_trait]
pub trait ResourcePort: Send + Sync {
    async fn read(&self, uri: &str) -> Result<Value>;
    async fn list(&self) -> Result<Vec<McpResource>>;
    async fn subscribe(&self, uri: &str) -> Result<tokio::sync::mpsc::Receiver<Value>>;
}
```

`list` is a snapshot — consumers that need live updates should also
call `subscribe`. Implementations that don't support subscriptions
return a receiver that closes immediately.

## Migration checklist (consumers of McpKit AgentMCP)

- [ ] Replace direct imports of `agentmcp.ports.server.Server` with
      `agentkit::domain::ports::ServerPort`.
- [ ] Replace `agentmcp.ports.resource.Resource` with
      `agentkit::domain::ports::ResourcePort`.
- [ ] Replace `agentmcp.domain.models.McpTool` /
      `McpResource` with the `agentkit` types (structurally identical).
- [ ] If you depended on the FastMCP adapter, depend on the
      `agentkit::adapters::mcp::fastmcp` shim (added in a follow-up PR).
- [ ] Drop any direct dependency on `McpKit` from Agentora consumers.
      McpKit is now a reference, not a runtime dep.

## Out of scope (this issue)

- Concrete adapter implementations (`fastmcp`, `cli`, `http`) — staged
  in follow-up PRs once the ports are stable.
- `subscribe` semantics for transports that don't natively support
  streaming — tracked in the follow-up issues, not blocking this port
  surface.
- Retired `PhenoMCPServers/servers/` lane — see
  `PhenoMCPServers/docs/retire/RETIRED-MCP-REPOS.md` for that
  retirement audit (separate repo, separate PR).

## Related

- ADR-017 — AgentMCP is the agent-runtime MCP lane.
- `crates/ABSORPTION_MANIFEST.md` — staged-crate policy.
- `docs/absorption/PHENOPROC_GAP_PORT.md` — sibling absorption plan.
- `PhenoMCPServers/docs/retire/RETIRED-MCP-REPOS.md` — retirement of
  the old servers lane (canonicalized out, not absorbed into Agentora).
