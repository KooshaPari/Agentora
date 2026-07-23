//! #79 hexagonal SDK ports (traits only).
//!
//! Surfaces call these ports only. Façade packages (LC-shaped) must not
//! leak LangChain types into these traits (ADR-78 Option C).
//! Bridges live in `sdk_bridges`.

use async_trait::async_trait;
use serde_json::Value;

use crate::agent::AgentError;
use crate::sdk_dto::{
    AgentMessage, CellRecord, EvalHookRef, ModelRequest, ModelResponse, RunHandle, SdkToolCall,
    ToolSpec,
};

/// Model invoke port.
#[async_trait]
pub trait ModelPort: Send + Sync {
    /// Invoke the model once.
    async fn invoke(&self, request: ModelRequest) -> Result<ModelResponse, AgentError>;
}

/// Tool registry + execution port.
#[async_trait]
pub trait ToolPort: Send + Sync {
    /// List tool specs.
    async fn list(&self) -> Result<Vec<ToolSpec>, AgentError>;
    /// Call one tool; returns a tool-role message.
    async fn call(&self, call: SdkToolCall) -> Result<AgentMessage, AgentError>;
}

/// Session-scoped memory port (#79).
pub trait SessionMemoryPort: Send + Sync {
    /// Replace session transcript.
    fn set(&self, session_id: &str, messages: Vec<AgentMessage>) -> Result<(), AgentError>;
    /// Read session transcript.
    fn get(&self, session_id: &str) -> Result<Vec<AgentMessage>, AgentError>;
    /// Append one message.
    fn append(&self, session_id: &str, message: AgentMessage) -> Result<(), AgentError>;
}

/// Scheduler / queue port (helios harness_queue kinship).
#[async_trait]
pub trait SchedulerQueuePort: Send + Sync {
    /// Enqueue opaque work; returns handle.
    async fn enqueue(&self, payload: Value) -> Result<RunHandle, AgentError>;
    /// Poll handle status / payload.
    async fn poll(&self, run_id: &str) -> Result<RunHandle, AgentError>;
    /// Cancel a run.
    async fn cancel(&self, run_id: &str) -> Result<(), AgentError>;
}

/// Observability port (Langfuse / cockpit).
#[async_trait]
pub trait ObservabilityPort: Send + Sync {
    /// Start a span; returns span id.
    async fn start_span(&self, name: &str, attributes: Value) -> Result<String, AgentError>;
    /// Attach a numeric score to a span/trace.
    async fn score(
        &self,
        span_id: &str,
        name: &str,
        value: f64,
        comment: Option<String>,
    ) -> Result<(), AgentError>;
    /// Flush buffered telemetry (fail loud on backend error).
    async fn flush(&self) -> Result<(), AgentError>;
}

/// Garden / eval attach port (does not own scoring).
#[async_trait]
pub trait EvalGardenPort: Send + Sync {
    /// Attach an eval/garden hook to the current run.
    async fn attach(&self, hook: EvalHookRef) -> Result<(), AgentError>;
    /// Record one cell payload for Garden / EvaluationReport producers.
    async fn record_cell(&self, cell: CellRecord) -> Result<(), AgentError>;
    /// Submit gate evidence blob (G1–G7 shape is producer-defined JSON).
    async fn gate_evidence(&self, evidence: Value) -> Result<(), AgentError>;
}
