//! Agent runtime port traits — LLM, tools, memory, and MCP contract surface.
//!
//! Extracted from Agentora domain ports (`src/domain/ports/mod.rs`).

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;

/// Agent contract error.
#[derive(Error, Debug, Clone)]
pub enum AgentError {
    /// LLM provider error.
    #[error("LLM error: {0}")]
    LLM(String),
    /// Tool execution error.
    #[error("tool error: {0}")]
    Tool(String),
    /// Memory operation error.
    #[error("memory error: {0}")]
    Memory(String),
    /// MCP server error.
    #[error("MCP error: {0}")]
    Mcp(String),
    /// Configuration error.
    #[error("config error: {0}")]
    Config(String),
}

/// Result type for agent contract operations.
pub type Result<T> = std::result::Result<T, AgentError>;

/// Memory entry role.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MemoryRole {
    /// User message.
    User,
    /// Assistant message.
    Assistant,
    /// System message.
    System,
}

/// Memory entry contract type.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    /// Speaker role.
    pub role: MemoryRole,
    /// Message content.
    pub content: String,
    /// Entry timestamp (UTC).
    pub timestamp: DateTime<Utc>,
    /// Optional metadata.
    pub metadata: Value,
}

/// Tool call request.
#[derive(Debug, Clone)]
pub struct ToolCall {
    /// Tool name.
    pub name: String,
    /// Tool parameters.
    pub params: Value,
    /// Correlation id.
    pub id: String,
}

/// Tool response.
#[derive(Debug, Clone)]
pub struct ToolResponse {
    /// Correlation id matching the call.
    pub id: String,
    /// Result payload.
    pub result: Value,
    /// Optional error message.
    pub error: Option<String>,
}

/// Agent execution context.
#[derive(Debug, Clone)]
pub struct Context {
    /// User input.
    pub input: String,
    /// Memory entries.
    pub memory: Vec<MemoryEntry>,
    /// Tool calls made.
    pub tool_calls: Vec<ToolCall>,
    /// Tool results.
    pub tool_results: Vec<ToolResponse>,
    /// Session id.
    pub session_id: String,
    /// Arbitrary metadata.
    pub metadata: Value,
}

/// LLM generation result.
#[derive(Debug, Clone)]
pub struct GenerationResult {
    /// Text content, if any.
    pub content: Option<String>,
    /// Tool calls requested by the model.
    pub tool_calls: Vec<ToolCall>,
}

/// LLM port — language model integration.
#[async_trait]
pub trait LLM: Send + Sync {
    /// Generate a completion from a prompt.
    async fn complete(&self, prompt: &str) -> Result<String>;
    /// Generate with full agent context.
    async fn generate(&self, context: &Context) -> Result<String>;
    /// Generate with tool support.
    async fn generate_with_tools(
        &self,
        context: &Context,
        tools: Vec<Value>,
    ) -> Result<GenerationResult>;
}

/// Memory port — short and long term memory.
pub trait MemoryPort: Send + Sync {
    /// Add an entry to memory.
    fn add(&self, entry: MemoryEntry) -> Result<()>;
    /// Get recent entries.
    fn recent(&self, limit: usize) -> Result<Vec<MemoryEntry>>;
    /// Search memories.
    fn search(&self, query: &str) -> Result<Vec<MemoryEntry>>;
}

/// Tool executor port.
#[async_trait]
pub trait ToolExecutor: Send + Sync {
    /// Execute a tool call.
    async fn execute(&self, call: ToolCall) -> Result<ToolResponse>;
}

/// MCP tool descriptor exposed to a model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpTool {
    /// Tool name.
    pub name: String,
    /// Human-readable description.
    pub description: String,
    /// JSON Schema parameters.
    pub parameters: Value,
}

/// MCP resource descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpResource {
    /// Resource URI.
    pub uri: String,
    /// Display name.
    pub name: String,
    /// Description.
    pub description: String,
    /// MIME type.
    pub mime_type: String,
}

/// Request to invoke an MCP-exposed tool.
#[derive(Debug, Clone)]
pub struct McpToolRequest {
    /// Tool name.
    pub name: String,
    /// Invocation parameters.
    pub params: Value,
}

/// Response from an MCP tool invocation.
#[derive(Debug, Clone)]
pub struct McpToolResponse {
    /// Response content.
    pub content: Value,
    /// Whether the response represents an error.
    pub is_error: bool,
}

/// MCP server port — owns server lifecycle.
#[async_trait]
pub trait ServerPort: Send + Sync {
    /// Start serving requests.
    async fn start(&self) -> Result<()>;
    /// Stop the server.
    async fn stop(&self) -> Result<()>;
    /// Register a tool.
    async fn register_tool(&self, tool: McpTool) -> Result<()>;
    /// List exposed tools.
    async fn list_tools(&self) -> Result<Vec<McpTool>>;
    /// Invoke a tool by name.
    async fn call_tool(&self, req: McpToolRequest) -> Result<McpToolResponse>;
}

/// MCP resource port — read-only access to named resources.
#[async_trait]
pub trait ResourcePort: Send + Sync {
    /// Read a resource by URI.
    async fn read(&self, uri: &str) -> Result<Value>;
    /// List available resource URIs.
    async fn list(&self) -> Result<Vec<McpResource>>;
    /// Subscribe to change notifications for a URI.
    async fn subscribe(&self, uri: &str) -> Result<tokio::sync::mpsc::Receiver<Value>>;
}
