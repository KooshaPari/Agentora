//! Health Check Abstractions and Project Health Types
//!
//! This crate provides core types for health checking across the Phenotype ecosystem.
//! It includes both service-level health checks and project-level health tracking
//! for the unified health dashboard.
//!
//! # Modules
//!
//! - [`checkers`] - Service-level health check implementations
//! - [`project`] - Project-level health types for dashboard integration

pub mod checkers;
pub mod project;

pub use checkers::{
    CacheHealthChecker, DatabaseHealthChecker, ExternalServiceHealthChecker, MemoryHealthChecker,
};
pub use project::{HealthBand, HealthDimension, LanguageStack, ProjectHealth};

use serde::Serialize;
use std::future::Future;
use std::pin::Pin;
use std::time::Duration;
use thiserror::Error;

pub use checkers::HealthCheck;
pub use project::{DimensionScore, Finding, Severity};

/// Errors that can occur during health checks.
#[derive(Debug, Error)]
pub enum HealthError {
    #[error("health check timed out after {0:?}")]
    Timeout(Duration),

    #[error("health check failed: {0}")]
    CheckFailed(String),

    #[error("health check panicked: {0}")]
    Panicked(String),
}

/// Result type for health checks.
pub type HealthResult<T> = Result<T, HealthError>;

/// Health status of a service or component.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum HealthStatus {
    /// Service is healthy and functioning normally.
    Healthy,
    /// Service is degraded but still functioning.
    Degraded,
    /// Service is unhealthy and requires attention.
    Unhealthy,
    /// Health status is unknown.
    Unknown,
}

impl Default for HealthStatus {
    fn default() -> Self {
        HealthStatus::Unknown
    }
}

/// Health check configuration.
#[derive(Debug, Clone)]
pub struct HealthCheckConfig {
    /// Timeout for the health check.
    pub timeout: Duration,
    /// Whether to include verbose output.
    pub verbose: bool,
}

impl Default for HealthCheckConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            verbose: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_health_status_default() {
        assert_eq!(HealthStatus::default(), HealthStatus::Unknown);
    }

    #[test]
    fn test_health_status_serialization() {
        let status = HealthStatus::Healthy;
        let json = serde_json::to_string(&status).unwrap();
        assert_eq!(json, "\"healthy\"");
    }
}
