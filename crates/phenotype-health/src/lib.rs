//! Health check utilities for Phenotype

use serde::{Deserialize, Serialize};

/// Health status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HealthStatus {
    /// Service is healthy
    Healthy,
    /// Service is degraded
    Degraded,
    /// Service is unhealthy
    Unhealthy,
}

/// Health check result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheck {
    pub status: HealthStatus,
    pub message: String,
}

/// Health check trait
pub trait HealthCheckable: Send + Sync {
    /// Perform health check
    fn check(&self) -> HealthCheck;
}
