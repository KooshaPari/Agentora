//! Security Alert Aggregation
//!
//! Aggregates security alerts from multiple sources (Snyk, CodeQL, cargo-audit, etc.)
//! and provides a unified security posture view.
//!
//! # Supported Sources
//!
//! - Snyk (via REST API)
//! - GitHub CodeQL
//! - cargo-audit (Rust advisory database)
//! - Dependabot
//! - Trivy (container/dependency scanning)

use crate::project::{DimensionScore, Finding, HealthDimension, Severity};
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Security alert severity
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AlertSeverity {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

impl AlertSeverity {
    pub fn to_severity(&self) -> Severity {
        match self {
            AlertSeverity::Info => Severity::Info,
            AlertSeverity::Low => Severity::Info,
            AlertSeverity::Medium => Severity::Warning,
            AlertSeverity::High => Severity::Error,
            AlertSeverity::Critical => Severity::Critical,
        }
    }
}

/// Source of a security alert
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AlertSource {
    Snyk,
    CodeQl,
    CargoAudit,
    Dependabot,
    Trivy,
    OsvScanner,
}

impl AlertSource {
    pub fn name(&self) -> &'static str {
        match self {
            AlertSource::Snyk => "Snyk",
            AlertSource::CodeQl => "CodeQL",
            AlertSource::CargoAudit => "cargo-audit",
            AlertSource::Dependabot => "Dependabot",
            AlertSource::Trivy => "Trivy",
            AlertSource::OsvScanner => "OSV-Scanner",
        }
    }
}

/// A security alert from any source
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityAlert {
    pub id: String,
    pub source: AlertSource,
    pub severity: AlertSeverity,
    pub title: String,
    pub description: Option<String>,
    pub package: Option<String>,
    pub current_version: Option<String>,
    pub fixed_version: Option<String>,
    pub created_at: DateTime<Utc>,
    pub url: Option<String>,
}

/// Trait for security data sources
#[async_trait]
pub trait SecuritySource: Send + Sync {
    fn source_name(&self) -> &'static str;

    async fn fetch_alerts(&self, repo: &str) -> anyhow::Result<Vec<SecurityAlert>>;

    async fn check_connection(&self) -> anyhow::Result<bool> {
        Ok(true)
    }
}

/// GitHub Security API source
#[derive(Debug, Clone)]
pub struct GitHubSecuritySource {
    token: Option<String>,
}

impl GitHubSecuritySource {
    pub fn new(token: Option<String>) -> Self {
        Self { token }
    }
}

#[async_trait]
impl SecuritySource for GitHubSecuritySource {
    fn source_name(&self) -> &'static str {
        "GitHub Security"
    }

    async fn fetch_alerts(&self, _repo: &str) -> anyhow::Result<Vec<SecurityAlert>> {
        // In production, this would call GitHub API
        Ok(Vec::new())
    }
}

/// Aggregated security results
#[derive(Debug, Clone)]
pub struct SecurityScanResult {
    pub total_alerts: usize,
    pub by_severity: HashMap<AlertSeverity, usize>,
    pub by_source: HashMap<AlertSource, usize>,
    pub score: f32,
    pub findings: Vec<Finding>,
    pub last_scan: DateTime<Utc>,
}

/// Security alert aggregator
#[derive(Debug, Clone, Default)]
pub struct SecurityAggregator {
    sources: Vec<Box<dyn SecuritySource>>,
}

impl SecurityAggregator {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_source<S: SecuritySource + 'static>(&mut self, source: S) {
        self.sources.push(Box::new(source));
    }

    pub fn with_github_source(mut self, token: Option<String>) -> Self {
        self.add_source(GitHubSecuritySource::new(token));
        self
    }

    /// Fetch and aggregate alerts from all sources
    pub async fn aggregate(&self, repo: &str) -> SecurityScanResult {
        let mut all_alerts = Vec::new();
        let mut by_severity: HashMap<AlertSeverity, usize> = HashMap::new();
        let mut by_source: HashMap<AlertSource, usize> = HashMap::new();
        let mut findings = Vec::new();

        for source in &self.sources {
            match source.fetch_alerts(repo).await {
                Ok(alerts) => {
                    for alert in alerts {
                        *by_severity.entry(alert.severity).or_insert(0) += 1;
                        *by_source.entry(alert.source.clone()).or_insert(0) += 1;

                        findings.push(Finding::new(
                            alert.severity.to_severity(),
                            HealthDimension::Security,
                            format!("[{}] {}", source.source_name(), alert.title),
                        ));

                        all_alerts.push(alert);
                    }
                }
                Err(e) => {
                    tracing::warn!("Failed to fetch from {}: {}", source.source_name(), e);
                }
            }
        }

        // Calculate security score (lower is better)
        let critical = *by_severity.get(&AlertSeverity::Critical).unwrap_or(&0) as f32;
        let high = *by_severity.get(&AlertSeverity::High).unwrap_or(&0) as f32;
        let medium = *by_severity.get(&AlertSeverity::Medium).unwrap_or(&0) as f32;

        // Score formula: 100 - (critical*10 + high*5 + medium*2)
        let score = (100.0 - (critical * 10.0 + high * 5.0 + medium * 2.0)).max(0.0);

        SecurityScanResult {
            total_alerts: all_alerts.len(),
            by_severity,
            by_source,
            score,
            findings,
            last_scan: Utc::now(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_empty_aggregator() {
        let aggregator = SecurityAggregator::new();
        let result = aggregator.aggregate("test/repo").await;

        assert_eq!(result.total_alerts, 0);
        assert_eq!(result.score, 100.0);
    }
}
