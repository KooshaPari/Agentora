//! Domain ports - Interfaces

use async_trait::async_trait;
use crate::domain::{Context, Result, ToolCall, ToolResponse, MemoryEntry};

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
