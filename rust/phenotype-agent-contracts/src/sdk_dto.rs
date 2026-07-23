//! #79 SDK surface matrix DTOs (wire: snake_case JSON).
//!
//! Spec: Phenotype session `06_SDK_SURFACE_MATRIX.md`.
//! No LangChain types — façades live outside this module (ADR-78 Option C).

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Evidence labels shared with EvaluationReport / Garden.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceLabel {
    /// Live verified run.
    #[serde(rename = "live verified")]
    LiveVerified,
    /// Historical artifact.
    Historical,
    /// Reported / synthetic.
    Reported,
    /// Inferred.
    Inferred,
    /// Unknown.
    Unknown,
}

/// Message role on the wire.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MessageRole {
    /// System prompt.
    System,
    /// User.
    User,
    /// Assistant.
    Assistant,
    /// Tool result.
    Tool,
}

/// Portable agent message DTO.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AgentMessage {
    /// Speaker role.
    pub role: MessageRole,
    /// Text content (parts deferred).
    pub content: String,
    /// Optional message id.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    /// Required when `role == tool`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
}

/// Tool JSON-Schema description.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolSpec {
    /// Tool name.
    pub name: String,
    /// Human description.
    pub description: String,
    /// JSON Schema object for arguments.
    pub input_schema: Value,
}

/// Tool invocation DTO (#79 — distinct from legacy `agent::ToolCall`).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SdkToolCall {
    /// Correlation id.
    pub id: String,
    /// Tool name.
    pub name: String,
    /// Arguments object.
    pub arguments: Value,
}

/// Optional generation parameters.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct ModelParams {
    /// Sampling temperature.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f32>,
    /// Max output tokens.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
}

/// Model invoke request.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ModelRequest {
    /// Conversation.
    pub messages: Vec<AgentMessage>,
    /// Optional tools.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tools: Option<Vec<ToolSpec>>,
    /// Model id.
    pub model: String,
    /// Optional params.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub params: Option<ModelParams>,
}

/// Token usage snapshot.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Usage {
    /// Prompt tokens.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prompt_tokens: Option<u32>,
    /// Completion tokens.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub completion_tokens: Option<u32>,
}

/// Model invoke response.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ModelResponse {
    /// Assistant message.
    pub message: AgentMessage,
    /// Optional tool calls.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<SdkToolCall>>,
    /// Optional usage.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub usage: Option<Usage>,
    /// Finish reason string.
    pub finish_reason: String,
}

/// Run lifecycle status.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RunStatus {
    /// Queued.
    Queued,
    /// Running.
    Running,
    /// Succeeded.
    Succeeded,
    /// Failed.
    Failed,
    /// Cancelled.
    Cancelled,
}

/// Handle for scheduled / queued work.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunHandle {
    /// Run id.
    pub run_id: String,
    /// Status.
    pub status: RunStatus,
}

/// Garden / EvaluationReport hook (does not own scoring).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvalHookRef {
    /// Optional garden run id.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub garden_run_id: Option<String>,
    /// Evidence label.
    pub evidence_label: EvidenceLabel,
    /// Suite name.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub suite: Option<String>,
    /// Task id.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub task_id: Option<String>,
}

/// Cell record for Garden attach (opaque JSON payload).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CellRecord {
    /// Suite.
    pub suite: String,
    /// Task id.
    pub task_id: String,
    /// Opaque cell body.
    pub payload: Value,
}
