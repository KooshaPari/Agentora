use serde::{Deserialize, Serialize};

/// Status of a single service.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ServiceStatus {
    Healthy,
    Degraded,
    Unhealthy,
    Unknown,
    Ready,
}

impl std::fmt::Display for ServiceStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ServiceStatus::Healthy => write!(f, "Healthy"),
            ServiceStatus::Degraded => write!(f, "Degraded"),
            ServiceStatus::Unhealthy => write!(f, "Unhealthy"),
            ServiceStatus::Unknown => write!(f, "Unknown"),
            ServiceStatus::Ready => write!(f, "Ready"),
        }
    }
}

/// Per-service health row.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceHealth {
    pub name: String,
    pub status: ServiceStatus,
    /// Latency in milliseconds, None if timed out.
    pub latency_ms: Option<u64>,
    pub uptime: Option<String>,
    pub port: Option<u16>,
    pub last_check: Option<String>,
}

/// Overall platform health summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformHealth {
    pub services: Vec<ServiceHealth>,
    pub overall: OverallStatus,
}

/// Overall platform status.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OverallStatus {
    Healthy,
    Degraded,
    Down,
}

impl std::fmt::Display for OverallStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OverallStatus::Healthy => write!(f, "HEALTHY"),
            OverallStatus::Degraded => write!(f, "DEGRADED"),
            OverallStatus::Down => write!(f, "DOWN"),
        }
    }
}
