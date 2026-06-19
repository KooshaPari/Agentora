# P4 contracts slice 4 — HTTP/agent adapter traits (Agentora)

**Date:** 2026-06-18  
**Disposition:** D-01 slice 4  
**Source interim:** HexaKit `crates/phenotype-contracts` (ports/adapters) + Agentora domain HTTP/agent ports  
**Terminal owner:** Agentora  
**Plan:** [phenotype-registry contracts-decompose-plan](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/disposition/contracts-decompose-plan.md)

## Target layout

| Surface | Canonical path |
|---------|----------------|
| Hexagonal port markers (`Command`, `Query`, `RepositoryPort`, …) | `rust/phenotype-agent-contracts/src/ports/` |
| Outbound driven ports (`Repository`, `CachePort`, `EventBus`, `SecretManager`, `ConfigLoader`) | `rust/phenotype-agent-contracts/src/outbound.rs` |
| InMemory test adapters | `rust/phenotype-agent-contracts/src/adapters.rs` |
| HTTP client port traits (`HttpClientPort`, `InterceptorPort`, …) | `rust/phenotype-agent-contracts/src/http.rs` |
| Agent runtime port traits (`LLM`, `ToolExecutor`, `ServerPort`, `ResourcePort`, …) | `rust/phenotype-agent-contracts/src/agent.rs` |

## Scope

- **In:** trait-only HTTP/agent adapter contracts extracted from HexaKit ports/adapters and Agentora domain ports.
- **Out:** generic `Contract` / `Event` / `MetricsHook` (remain phenoShared interim per slice 1).
- **Out:** reqwest/mock HTTP implementations (stay in `phenotype-http-client` infrastructure).
- **Out:** Agentora `src/domain/ports/mod.rs` re-export wiring (future slice).

## Consumer repoint

| Consumer | Action |
|----------|--------|
| substrate MCP plane | Git-pin `phenotype-agent-contracts` from Agentora for runtime edge traits |
| Agentora `src/domain/ports.rs` | Future slice: depend on / re-export contracts crate |

## Verification

```bash
cargo check -p phenotype-agent-contracts
```

## Registry

Row **#11** (`phenotype-contracts`) stays `fsm: relocating` until slice 3 (Eventra) lands and consumers repoint.
