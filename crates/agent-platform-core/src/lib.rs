//! `agent-platform-core` — the domain layer.
//!
//! Holds pure data types and invariants for agents, contexts, sessions, and
//! messages. No I/O, no transport, no async runtime. The core crate is the
//! innermost hexagon: adapters depend on it, never the reverse.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A unique identifier for an agent instance participating in the platform.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct AgentId(pub Uuid);

/// A unique identifier for a session — a bounded conversation between actors.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SessionId(pub Uuid);

/// A free-form key/value bag that flows with each request as ambient context.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Context(pub BTreeMap<String, String>);

/// Placeholder entry point so the crate is buildable on day one.
pub fn placeholder() {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_are_distinct() {
        let a = AgentId(Uuid::new_v4());
        let b = AgentId(Uuid::new_v4());
        assert_ne!(a, b);
    }
}
