//! Domain ports - Interfaces

use crate::domain::{Context, MemoryEntry, Result, ToolCall, ToolResponse};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};

/// LLM port - for language model integration
#[async_trait]
pub trait LLM: Send + Sync {
    /// Generate a completion
    async fn complete(&self, prompt: &str) -> Result<String>;

    /// Generate with context
    async fn generate(&self, context: &Context) -> Result<String>;

    /// Generate with tool support
    async fn generate_with_tools(
        &self,
        context: &Context,
        tools: Vec<serde_json::Value>,
    ) -> Result<GenerationResult>;
}

/// Generation result
#[derive(Debug)]
pub struct GenerationResult {
    pub content: Option<String>,
    pub tool_calls: Vec<ToolCall>,
}

impl GenerationResult {
    pub fn text(content: impl Into<String>) -> Self {
        Self {
            content: Some(content.into()),
            tool_calls: Vec::new(),
        }
    }

    pub fn with_tools(content: Option<String>, tool_calls: Vec<ToolCall>) -> Self {
        Self {
            content,
            tool_calls,
        }
    }
}

/// Memory port - for memory implementations
pub trait MemoryPort: Send + Sync {
    /// Add an entry to memory
    fn add(&self, entry: MemoryEntry) -> Result<()>;

    /// Get recent entries
    fn recent(&self, limit: usize) -> Result<Vec<MemoryEntry>>;

    /// Search memories
    fn search(&self, query: &str) -> Result<Vec<MemoryEntry>>;
}

/// Tool executor port
#[async_trait]
pub trait ToolExecutor: Send + Sync {
    /// Execute a tool call
    async fn execute(&self, call: ToolCall) -> Result<ToolResponse>;
}

// ---------------------------------------------------------------------------
// MCP (Model Context Protocol) ports
// ---------------------------------------------------------------------------
//
// These ports formalise the integration path for `AgentMCP` patterns
// absorbed from McpKit (`python/agentmcp/`). They live in the domain layer
// (no infrastructure deps) so that adapters — `FastMCP`, `CLI`, etc. —
// can be swapped without touching application code. See
// `docs/mcp/INTEGRATION.md` for the full migration note (issue #86,
// ADR-017).

/// MCP tool descriptor exposed to a model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpTool {
    pub name: String,
    pub description: String,
    pub parameters: serde_json::Value,
}

/// MCP resource descriptor (read-only context, per ADR-017).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpResource {
    pub uri: String,
    pub name: String,
    pub description: String,
    pub mime_type: String,
}

/// Request to invoke an MCP-exposed tool.
#[derive(Debug, Clone)]
pub struct McpToolRequest {
    pub name: String,
    pub params: serde_json::Value,
}

/// Response from an MCP tool invocation.
#[derive(Debug, Clone)]
pub struct McpToolResponse {
    pub content: serde_json::Value,
    pub is_error: bool,
}

/// Server port — owns the lifecycle of an MCP server.
///
/// Mirrors `McpKit.agentmcp.ports.server.Server` but expressed as a
/// `dyn`-safe async trait so the agent runtime can hold any concrete
/// transport (FastMCP, stdio, HTTP, …) behind a single trait object.
#[async_trait]
pub trait ServerPort: Send + Sync {
    /// Start serving requests. Implementations should be idempotent —
    /// a second call to `start` on an already-running server is a no-op.
    async fn start(&self) -> Result<()>;

    /// Stop the server and release transport resources.
    async fn stop(&self) -> Result<()>;

    /// Register a tool that the server will expose.
    async fn register_tool(&self, tool: McpTool) -> Result<()>;

    /// List tools currently exposed.
    async fn list_tools(&self) -> Result<Vec<McpTool>>;

    /// Invoke a tool by name.
    async fn call_tool(&self, req: McpToolRequest) -> Result<McpToolResponse>;
}

/// Resource port — read-only access to named resources (files, URLs, …).
///
/// Mirrors `McpKit.agentmcp.ports.resource.Resource`. Kept distinct from
/// `ServerPort` so a transport can be resource-only (e.g. a documentation
/// provider) without the overhead of the full server lifecycle.
#[async_trait]
pub trait ResourcePort: Send + Sync {
    /// Read a resource by URI.
    async fn read(&self, uri: &str) -> Result<serde_json::Value>;

    /// List the URIs this port can serve.
    async fn list(&self) -> Result<Vec<McpResource>>;

    /// Subscribe to change notifications for a URI. Returns a receiver
    /// that yields the updated payload. Implementations that do not
    /// support live updates may return an empty stream.
    async fn subscribe(&self, uri: &str) -> Result<tokio::sync::mpsc::Receiver<serde_json::Value>>;
}
