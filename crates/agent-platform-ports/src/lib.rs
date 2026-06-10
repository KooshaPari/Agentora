//! `agent-platform-ports` — inbound and outbound port definitions.
//!
//! Ports are async traits that describe what the application needs from the
//! outside world (outbound) and what the outside world can ask of the
//! application (inbound). Adapters implement them; the core never sees them.

use agent_platform_core::{AgentId, Context, SessionId};
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// All port-level errors collapse to this enum so the application layer can
/// handle them uniformly.
#[derive(Debug, Error)]
pub enum PortError {
    #[error("transport failure: {0}")]
    Transport(String),
    #[error("invalid input: {0}")]
    Invalid(String),
    #[error("upstream provider rejected the request: {0}")]
    Provider(String),
    #[error("not found: {0}")]
    NotFound(String),
    #[error(transparent)]
    Other(#[from] Box<dyn std::error::Error + Send + Sync>),
}

/// A single prompt + context round-trip with an LLM provider.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmRequest {
    pub prompt: String,
    pub context: Context,
}

/// The provider's reply.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmReply {
    pub text: String,
    pub model: String,
    pub tokens_used: u32,
}

/// Outbound port: talk to any LLM (cheap-llm, Claude, OpenAI, local).
pub trait LlmProvider: Send + Sync {
    async fn complete(&self, req: LlmRequest) -> Result<LlmReply, PortError>;
}

/// Outbound port: durable, queryable session storage.
pub trait SessionStore: Send + Sync {
    async fn load(&self, id: SessionId) -> Result<Option<Vec<u8>>, PortError>;
    async fn save(&self, id: SessionId, blob: Vec<u8>) -> Result<(), PortError>;
}

/// Inbound port: a transport that delivers a request and expects a reply.
pub trait InboundTransport: Send + Sync {
    async fn serve(&self) -> Result<(), PortError>;
    fn agent_id(&self) -> AgentId;
}

pub fn placeholder() {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn port_error_displays() {
        let e = PortError::Invalid("nope".into());
        assert!(e.to_string().contains("nope"));
    }
}
