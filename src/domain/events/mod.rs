//! Domain events

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Agent started event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStarted {
    pub agent_name: String,
    pub session_id: String,
    pub occurred_at: DateTime<Utc>,
}

impl AgentStarted {
    pub fn new(agent_name: String, session_id: String) -> Self {
        Self {
            agent_name,
            session_id,
            occurred_at: Utc::now(),
        }
    }
}

/// Agent completed event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentCompleted {
    pub agent_name: String,
    pub session_id: String,
    pub duration_ms: u64,
    pub steps: u32,
    pub occurred_at: DateTime<Utc>,
}

impl AgentCompleted {
    pub fn new(agent_name: String, session_id: String, duration_ms: u64, steps: u32) -> Self {
        Self {
            agent_name,
            session_id,
            duration_ms,
            steps,
            occurred_at: Utc::now(),
        }
    }
}

/// Tool called event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCalled {
    pub tool_name: String,
    pub session_id: String,
    pub arguments: serde_json::Value,
    pub occurred_at: DateTime<Utc>,
}

impl ToolCalled {
    pub fn new(tool_name: String, session_id: String, arguments: serde_json::Value) -> Self {
        Self {
            tool_name,
            session_id,
            arguments,
            occurred_at: Utc::now(),
        }
    }
}
