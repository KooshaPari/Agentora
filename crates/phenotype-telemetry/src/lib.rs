//! Telemetry utilities for Phenotype

use serde::{Deserialize, Serialize};

/// Telemetry event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TelemetryEvent {
    pub name: String,
    pub timestamp: u64,
    pub attributes: std::collections::HashMap<String, String>,
}

/// Telemetry collector trait
pub trait TelemetryCollector: Send + Sync {
    /// Record an event
    fn record(&self, event: TelemetryEvent);
}
