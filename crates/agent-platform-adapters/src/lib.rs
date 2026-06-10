//! `agent-platform-adapters` — concrete wiring of inbound/outbound ports.
//!
//! Each adapter lives in its own submodule. New transports, providers, and
//! storage backends slot in here without touching the domain or the
//! application crate.

use agent_platform_core::AgentId;
use agent_platform_ports::{InboundTransport, LlmProvider, LlmReply, LlmRequest, PortError, SessionStore};
use agent_platform_core::SessionId;

/// `cheap-llm-mcp` adapter — the first LLM provider to be absorbed.
/// Implements the [`LlmProvider`] port.
pub struct CheapLlmMcpAdapter {
    pub endpoint: String,
}

impl CheapLlmMcpAdapter {
    pub fn new(endpoint: impl Into<String>) -> Self {
        Self { endpoint: endpoint.into() }
    }
}

impl LlmProvider for CheapLlmMcpAdapter {
    async fn complete(&self, _req: LlmRequest) -> Result<LlmReply, PortError> {
        // TODO(agent-platform): wire reqwest call to cheap-llm-mcp /v1/complete.
        Err(PortError::Provider("CheapLlmMcpAdapter not yet wired".into()))
    }
}

/// File-system-backed session store. Useful for tests and local dev.
pub struct FileSessionStore {
    pub root: std::path::PathBuf,
}

impl SessionStore for FileSessionStore {
    async fn load(&self, _id: SessionId) -> Result<Option<Vec<u8>>, PortError> {
        Ok(None)
    }
    async fn save(&self, _id: SessionId, _blob: Vec<u8>) -> Result<(), PortError> {
        Ok(())
    }
}

/// MCP stdio transport — receives MCP messages from a parent process.
pub struct McpStdioTransport {
    pub agent: AgentId,
}

impl InboundTransport for McpStdioTransport {
    async fn serve(&self) -> Result<(), PortError> {
        Ok(())
    }
    fn agent_id(&self) -> AgentId {
        self.agent
    }
}

pub fn placeholder() {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cheap_llm_adapter_constructs() {
        let a = CheapLlmMcpAdapter::new("http://localhost:7777");
        assert_eq!(a.endpoint, "http://localhost:7777");
    }
}
