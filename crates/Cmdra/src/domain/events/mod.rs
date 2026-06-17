//! Domain events - Event sourcing support
//!
//! Events represent something that happened in the domain.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Base event trait
pub trait DomainEvent: Send + Sync {
    fn event_type(&self) -> &str;
    fn occurred_at(&self) -> DateTime<Utc>;
}

/// Command executed event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandExecuted {
    pub command: String,
    pub args: Vec<String>,
    pub exit_code: u8,
    pub duration_ms: u64,
    pub occurred_at: DateTime<Utc>,
}

impl DomainEvent for CommandExecuted {
    fn event_type(&self) -> &str {
        "CommandExecuted"
    }

    fn occurred_at(&self) -> DateTime<Utc> {
        self.occurred_at
    }
}

impl CommandExecuted {
    pub fn new(command: String, args: Vec<String>, exit_code: u8, duration_ms: u64) -> Self {
        Self {
            command,
            args,
            exit_code,
            duration_ms,
            occurred_at: Utc::now(),
        }
    }
}

/// Command failed event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandFailed {
    pub command: String,
    pub error: String,
    pub occurred_at: DateTime<Utc>,
}

impl DomainEvent for CommandFailed {
    fn event_type(&self) -> &str {
        "CommandFailed"
    }

    fn occurred_at(&self) -> DateTime<Utc> {
        self.occurred_at
    }
}

impl CommandFailed {
    pub fn new(command: String, error: String) -> Self {
        Self {
            command,
            error,
            occurred_at: Utc::now(),
        }
    }
}

/// Plugin loaded event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginLoaded {
    pub plugin_name: String,
    pub plugin_version: String,
    pub occurred_at: DateTime<Utc>,
}

impl DomainEvent for PluginLoaded {
    fn event_type(&self) -> &str {
        "PluginLoaded"
    }

    fn occurred_at(&self) -> DateTime<Utc> {
        self.occurred_at
    }
}

impl PluginLoaded {
    pub fn new(plugin_name: String, plugin_version: String) -> Self {
        Self {
            plugin_name,
            plugin_version,
            occurred_at: Utc::now(),
        }
    }
}
