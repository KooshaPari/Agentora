//! Bridges from legacy agent traits onto #79 SDK ports.
//!
//! Keep LangChain types out of this module (ADR-78 Option C).

use async_trait::async_trait;
use serde_json::Value;

use crate::agent::{
    AgentError, Context, GenerationResult, MemoryEntry, MemoryPort, MemoryRole, ToolCall,
    ToolExecutor, ToolResponse, LLM,
};
use crate::sdk_dto::{
    AgentMessage, MessageRole, ModelRequest, ModelResponse, SdkToolCall, ToolSpec,
};
use crate::sdk_ports::{ModelPort, SessionMemoryPort, ToolPort};

/// Bridge `LLM` → `ModelPort` (legacy complete/generate path).
pub struct LlmModelBridge<T: LLM> {
    inner: T,
}

impl<T: LLM> LlmModelBridge<T> {
    /// Wrap an existing LLM port.
    pub fn new(inner: T) -> Self {
        Self { inner }
    }
}

#[async_trait]
impl<T: LLM> ModelPort for LlmModelBridge<T> {
    async fn invoke(&self, request: ModelRequest) -> Result<ModelResponse, AgentError> {
        let prompt = flatten_messages(&request.messages);
        let tools: Vec<Value> = request
            .tools
            .unwrap_or_default()
            .into_iter()
            .map(|t| {
                serde_json::json!({
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                })
            })
            .collect();
        let ctx = Context {
            input: prompt.clone(),
            memory: messages_to_memory(&request.messages),
            tool_calls: vec![],
            tool_results: vec![],
            session_id: String::new(),
            metadata: serde_json::json!({"model": request.model}),
        };
        let gen: GenerationResult = if tools.is_empty() {
            let text = self.inner.generate(&ctx).await?;
            GenerationResult {
                content: Some(text),
                tool_calls: vec![],
            }
        } else {
            self.inner.generate_with_tools(&ctx, tools).await?
        };
        Ok(generation_to_response(gen))
    }
}

/// Bridge `ToolExecutor` → `ToolPort` with a static catalog.
pub struct ExecutorToolBridge<T: ToolExecutor> {
    inner: T,
    catalog: Vec<ToolSpec>,
}

impl<T: ToolExecutor> ExecutorToolBridge<T> {
    /// Wrap executor + catalog.
    pub fn new(inner: T, catalog: Vec<ToolSpec>) -> Self {
        Self { inner, catalog }
    }
}

#[async_trait]
impl<T: ToolExecutor> ToolPort for ExecutorToolBridge<T> {
    async fn list(&self) -> Result<Vec<ToolSpec>, AgentError> {
        Ok(self.catalog.clone())
    }

    async fn call(&self, call: SdkToolCall) -> Result<AgentMessage, AgentError> {
        let legacy = ToolCall {
            name: call.name,
            params: call.arguments,
            id: call.id.clone(),
        };
        let resp: ToolResponse = self.inner.execute(legacy).await?;
        let content = if let Some(err) = resp.error {
            return Err(AgentError::Tool(err));
        } else {
            resp.result.to_string()
        };
        Ok(AgentMessage {
            role: MessageRole::Tool,
            content,
            id: None,
            tool_call_id: Some(call.id),
        })
    }
}

/// Bridge `MemoryPort` → `SessionMemoryPort` (single shared store; session id tagged in metadata).
pub struct MemorySessionBridge<T: MemoryPort> {
    inner: T,
}

impl<T: MemoryPort> MemorySessionBridge<T> {
    /// Wrap legacy memory.
    pub fn new(inner: T) -> Self {
        Self { inner }
    }
}

impl<T: MemoryPort> SessionMemoryPort for MemorySessionBridge<T> {
    fn set(&self, session_id: &str, messages: Vec<AgentMessage>) -> Result<(), AgentError> {
        // Legacy MemoryPort has no clear(); fail loud if non-empty replace requested
        // against a store that already has entries from another session.
        let existing = self.inner.recent(usize::MAX)?;
        if !existing.is_empty() {
            let foreign = existing.iter().any(|e| {
                e.metadata
                    .get("session_id")
                    .and_then(|v| v.as_str())
                    .map(|s| s != session_id)
                    .unwrap_or(false)
            });
            if foreign {
                return Err(AgentError::Memory(
                    "MemorySessionBridge::set cannot clear foreign-session entries; use a session-scoped store".into(),
                ));
            }
        }
        for msg in messages {
            self.inner.add(message_to_memory(session_id, msg))?;
        }
        Ok(())
    }

    fn get(&self, session_id: &str) -> Result<Vec<AgentMessage>, AgentError> {
        let entries = self.inner.recent(usize::MAX)?;
        Ok(entries
            .into_iter()
            .filter(|e| e.metadata.get("session_id").and_then(|v| v.as_str()) == Some(session_id))
            .map(memory_to_message)
            .collect())
    }

    fn append(&self, session_id: &str, message: AgentMessage) -> Result<(), AgentError> {
        self.inner.add(message_to_memory(session_id, message))
    }
}

fn flatten_messages(messages: &[AgentMessage]) -> String {
    messages
        .iter()
        .map(|m| format!("{:?}: {}", m.role, m.content))
        .collect::<Vec<_>>()
        .join("\n")
}

fn messages_to_memory(messages: &[AgentMessage]) -> Vec<MemoryEntry> {
    messages
        .iter()
        .cloned()
        .map(|m| message_to_memory("", m))
        .collect()
}

fn message_to_memory(session_id: &str, message: AgentMessage) -> MemoryEntry {
    let role = match message.role {
        MessageRole::System => MemoryRole::System,
        MessageRole::User => MemoryRole::User,
        MessageRole::Assistant | MessageRole::Tool => MemoryRole::Assistant,
    };
    MemoryEntry {
        role,
        content: message.content,
        timestamp: chrono::Utc::now(),
        metadata: serde_json::json!({
            "session_id": session_id,
            "id": message.id,
            "tool_call_id": message.tool_call_id,
        }),
    }
}

fn memory_to_message(entry: MemoryEntry) -> AgentMessage {
    let role = match entry.role {
        MemoryRole::System => MessageRole::System,
        MemoryRole::User => MessageRole::User,
        MemoryRole::Assistant => MessageRole::Assistant,
    };
    AgentMessage {
        role,
        content: entry.content,
        id: entry
            .metadata
            .get("id")
            .and_then(|v| v.as_str())
            .map(str::to_string),
        tool_call_id: entry
            .metadata
            .get("tool_call_id")
            .and_then(|v| v.as_str())
            .map(str::to_string),
    }
}

fn generation_to_response(gen: GenerationResult) -> ModelResponse {
    let tool_calls = if gen.tool_calls.is_empty() {
        None
    } else {
        Some(
            gen.tool_calls
                .into_iter()
                .map(|t| SdkToolCall {
                    id: t.id,
                    name: t.name,
                    arguments: t.params,
                })
                .collect(),
        )
    };
    ModelResponse {
        message: AgentMessage {
            role: MessageRole::Assistant,
            content: gen.content.unwrap_or_default(),
            id: None,
            tool_call_id: None,
        },
        tool_calls,
        usage: None,
        finish_reason: "stop".into(),
    }
}
