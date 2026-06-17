//! Substrate port adapters — wraps agentkit domain behind substrate ports.

mod engine;
mod registry;
mod routing;
mod skill_registry;
mod store;
mod tool_registry;
mod transport;

pub use engine::AgentEngine;
pub use registry::InMemorySkillRegistry;
pub use routing::AgentRoutingPort;
pub use skill_registry::SkillRegistry;
pub use store::MemStore;
pub use tool_registry::ToolRegistry;
pub use transport::NoopTransport;
