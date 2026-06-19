//! HTTP and agent adapter contract traits for the Phenotype ecosystem.
//!
//! Terminal owner: **Agentora** (P4 contracts decompose slice 4).
//! Generic cross-cutting contracts (`Contract`, `Event`, `MetricsHook`) remain on
//! phenoShared interim per [ADR-ECO-014](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/adrs/ADR-ECO-014-phenoshared-decompose.md).

#![warn(missing_docs)]
#![warn(clippy::all)]

pub mod adapters;
pub mod agent;
pub mod error;
pub mod http;
pub mod outbound;
pub mod ports;

pub use adapters::{
    InMemoryCache, InMemoryEventBus, InMemoryRepository, InMemorySecretManager,
};
pub use agent::{
    AgentError, Context, GenerationResult, LLM, McpResource, McpTool, McpToolRequest,
    McpToolResponse, MemoryEntry, MemoryPort, MemoryRole, ResourcePort, ServerPort,
    ToolCall, ToolExecutor, ToolResponse,
};
pub use error::{DomainError, ErrorKind, Result};
pub use http::{
    Body, ConnectionPoolPort, ConnectionPort, Headers, HttpClientPort, HttpError,
    InterceptorPort, PoolStats, Request, RequestBuilder, Response,
};
pub use outbound::{CachePort, ConfigLoader, EventBus, Repository, SecretManager};
pub use ports::{Command, Query, RepositoryPort, SecretPort, UseCaseResult};
