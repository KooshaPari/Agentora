//! Project Registry and Discovery
//!
//! Provides project discovery and metadata extraction across the Phenotype ecosystem.
//!
//! This crate enables unified health dashboard tracking across all projects by
//! discovering projects and aggregating their health configurations.
//!
//! # Features
//!
//! - Project discovery across multiple language stacks (Rust, TypeScript, Python, Go)
//! - Health dashboard configuration aggregation
//! - Missing file tracking
//! - Git metadata extraction

mod project;
mod health_registry;

pub use project::{Project, ProjectType, ProjectRegistry};
pub use health_registry::{HealthDashboardConfig, HealthDashboardRegistry, HealthRegistrySummary};

use std::path::Path;

/// Discover all projects in the given root directory
pub async fn discover_projects(root: &Path) -> anyhow::Result<ProjectRegistry> {
    ProjectRegistry::discover(root).await
}

/// Discover health dashboard configurations in the given root directory
pub async fn discover_health_configs(root: &Path) -> anyhow::Result<HealthDashboardRegistry> {
    HealthDashboardRegistry::discover_in(root).await
}
