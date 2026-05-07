//! Context domain - Agent execution context

use serde_json::Value;
use std::collections::HashMap;

/// Execution context
#[derive(Debug, Clone)]
pub struct Context {
    /// User input
    pub input: String,
    /// Memory entries
    pub memory: Vec<crate::domain::MemoryEntry>,
    /// Tool calls made
    pub tool_calls: Vec<crate::domain::ToolCall>,
    /// Tool results
    pub tool_results: Vec<crate::domain::ToolResponse>,
    /// Session ID
    pub session_id: String,
    /// Metadata
    pub metadata: HashMap<String, Value>,
}

impl Context {
    pub fn new(input: impl Into<String>) -> Self {
        Self {
            input: input.into(),
            memory: Vec::new(),
            tool_calls: Vec::new(),
            tool_results: Vec::new(),
            session_id: uuid::Uuid::new_v4().to_string(),
            metadata: HashMap::new(),
        }
    }

    pub fn with_session(mut self, session_id: impl Into<String>) -> Self {
        self.session_id = session_id.into();
        self
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

/// Agent output
#[derive(Debug, Clone)]
pub struct Output {
    pub content: OutputContent,
    pub tool_calls: Vec<ToolCallOutput>,
    pub metrics: ExecutionMetrics,
}

impl Output {
    pub fn text(content: impl Into<String>) -> Self {
        Self {
            content: OutputContent::Text(content.into()),
            tool_calls: Vec::new(),
            metrics: ExecutionMetrics::default(),
        }
    }

    pub fn json(value: Value) -> Self {
        Self {
            content: OutputContent::Json(value),
            tool_calls: Vec::new(),
            metrics: ExecutionMetrics::default(),
        }
    }

    pub fn error(message: impl Into<String>) -> Self {
        Self {
            content: OutputContent::Error(message.into()),
            tool_calls: Vec::new(),
            metrics: ExecutionMetrics::default(),
        }
    }
}

#[derive(Debug, Clone)]
pub enum OutputContent {
    Text(String),
    Json(Value),
    Error(String),
}

/// Tool call output for response
#[derive(Debug, Clone)]
pub struct ToolCallOutput {
    pub name: String,
    pub arguments: Value,
    pub result: Value,
}

/// Execution metrics
#[derive(Debug, Clone, Default)]
pub struct ExecutionMetrics {
    pub steps: u32,
    pub tool_calls: u32,
    pub duration_ms: u64,
    pub tokens_used: u32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_context() {
        let ctx = Context::new("Hello, agent!")
            .with_session("session-123")
            .with_metadata("user_id", serde_json::json!("user-1"));

        assert_eq!(ctx.input, "Hello, agent!");
        assert_eq!(ctx.session_id, "session-123");
    }

    #[test]
    fn test_output() {
        let output = Output::text("Hello, user!");
        match output.content {
            OutputContent::Text(s) => assert_eq!(s, "Hello, user!"),
            _ => panic!("Expected text output"),
        }
    }
}
