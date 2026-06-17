//! Project-Level Health Types for Unified Health Dashboard
//!
//! This module provides types for tracking project health across the Phenotype ecosystem.
//! It enables unified compliance monitoring, security posture tracking, and dependency
//! freshness checking across all projects.
//!
//! # Health Dimensions
//!
//! - Documentation (15%): CLAUDE.md, README.md, CONTRIBUTING.md, LICENSE, CHANGELOG.md
//! - Test Coverage (20%): Code coverage percentage and trends
//! - Security (25%): Vulnerability counts from Snyk, CodeQL, cargo-audit
//! - Dependencies (15%): Outdated packages and license compliance
//! - Compliance (15%): Required files (deny.toml, codecov.yml, etc.)
//! - Code Quality (10%): Linter violations and complexity metrics

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Language stack for a project.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum LanguageStack {
    Rust,
    TypeScript,
    Python,
    Go,
    Multi,
}

impl std::fmt::Display for LanguageStack {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LanguageStack::Rust => write!(f, "Rust"),
            LanguageStack::TypeScript => write!(f, "TypeScript"),
            LanguageStack::Python => write!(f, "Python"),
            LanguageStack::Go => write!(f, "Go"),
            LanguageStack::Multi => write!(f, "Multi"),
        }
    }
}

/// Health band classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum HealthBand {
    Excellent, // 90-100
    Good,      // 75-89
    Fair,      // 60-74
    Poor,      // 40-59
    Critical,  // 0-39
}

impl HealthBand {
    pub fn from_score(score: f32) -> Self {
        match score {
            90.0..=100.0 => HealthBand::Excellent,
            75.0..=89.9 => HealthBand::Good,
            60.0..=74.9 => HealthBand::Fair,
            40.0..=59.9 => HealthBand::Poor,
            _ => HealthBand::Critical,
        }
    }

    pub fn color(&self) -> &'static str {
        match self {
            HealthBand::Excellent => "green",
            HealthBand::Good => "blue",
            HealthBand::Fair => "yellow",
            HealthBand::Poor => "orange",
            HealthBand::Critical => "red",
        }
    }

    pub fn icon(&self) -> &'static str {
        match self {
            HealthBand::Excellent => "✓",
            HealthBand::Good => "◐",
            HealthBand::Fair => "◑",
            HealthBand::Poor => "○",
            HealthBand::Critical => "✗",
        }
    }
}

/// Severity level for findings.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Info,
    Warning,
    Error,
    Critical,
}

impl Severity {
    pub fn weight(&self) -> f32 {
        match self {
            Severity::Info => 1.0,
            Severity::Warning => 2.0,
            Severity::Error => 5.0,
            Severity::Critical => 10.0,
        }
    }
}

/// A finding from a health check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub severity: Severity,
    pub dimension: HealthDimension,
    pub message: String,
    pub file: Option<String>,
    pub line: Option<u32>,
}

impl Finding {
    pub fn new(severity: Severity, dimension: HealthDimension, message: impl Into<String>) -> Self {
        Self {
            severity,
            dimension,
            message: message.into(),
            file: None,
            line: None,
        }
    }

    pub fn with_location(mut self, file: impl Into<String>, line: u32) -> Self {
        self.file = Some(file.into());
        self.line = Some(line);
        self
    }
}

/// Health dimension types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HealthDimension {
    Documentation,
    TestCoverage,
    Security,
    Dependencies,
    Compliance,
    CodeQuality,
}

impl HealthDimension {
    pub fn weight(&self) -> f32 {
        match self {
            HealthDimension::Documentation => 0.15,
            HealthDimension::TestCoverage => 0.20,
            HealthDimension::Security => 0.25,
            HealthDimension::Dependencies => 0.15,
            HealthDimension::Compliance => 0.15,
            HealthDimension::CodeQuality => 0.10,
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            HealthDimension::Documentation => "Documentation",
            HealthDimension::TestCoverage => "Test Coverage",
            HealthDimension::Security => "Security",
            HealthDimension::Dependencies => "Dependencies",
            HealthDimension::Compliance => "Compliance",
            HealthDimension::CodeQuality => "Code Quality",
        }
    }
}

/// Score for a specific health dimension.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DimensionScore {
    pub dimension: HealthDimension,
    pub score: f32,      // 0-100
    pub findings: Vec<Finding>,
}

impl DimensionScore {
    pub fn new(dimension: HealthDimension, score: f32) -> Self {
        Self {
            dimension,
            score: score.clamp(0.0, 100.0),
            findings: Vec::new(),
        }
    }

    pub fn with_findings(mut self, findings: Vec<Finding>) -> Self {
        self.findings = findings;
        self
    }
}

/// Aggregate health score for a repository.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectHealth {
    pub repo_name: String,
    pub owner: String,
    pub language: LanguageStack,
    pub overall_score: f32,
    pub band: HealthBand,
    pub dimensions: HashMap<HealthDimension, DimensionScore>,
    pub findings: Vec<Finding>,
    pub last_scan: DateTime<Utc>,
    pub scan_duration_ms: u64,
}

impl ProjectHealth {
    /// Create a new project health record.
    pub fn new(repo_name: impl Into<String>, owner: impl Into<String>, language: LanguageStack) -> Self {
        Self {
            repo_name: repo_name.into(),
            owner: owner.into(),
            language,
            overall_score: 0.0,
            band: HealthBand::Critical,
            dimensions: HashMap::new(),
            findings: Vec::new(),
            last_scan: Utc::now(),
            scan_duration_ms: 0,
        }
    }

    /// Compute the overall score from dimensions.
    pub fn compute_overall_score(&mut self) {
        if self.dimensions.is_empty() {
            self.overall_score = 0.0;
            self.band = HealthBand::Critical;
            return;
        }

        let mut total_weighted = 0.0;
        let mut total_weight = 0.0;

        for (dimension, score) in &self.dimensions {
            total_weighted += score.score * dimension.weight();
            total_weight += dimension.weight();
        }

        if total_weight > 0.0 {
            self.overall_score = (total_weighted / total_weight * 100.0).min(100.0);
        }
        self.band = HealthBand::from_score(self.overall_score);
    }

    /// Check if the project meets compliance threshold.
    pub fn is_compliant(&self, threshold: f32) -> bool {
        self.overall_score >= threshold
    }

    /// Get total findings count.
    pub fn total_findings(&self) -> usize {
        self.findings.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_health_band_from_score() {
        assert_eq!(HealthBand::from_score(95.0), HealthBand::Excellent);
        assert_eq!(HealthBand::from_score(82.0), HealthBand::Good);
        assert_eq!(HealthBand::from_score(70.0), HealthBand::Fair);
        assert_eq!(HealthBand::from_score(50.0), HealthBand::Poor);
        assert_eq!(HealthBand::from_score(25.0), HealthBand::Critical);
    }

    #[test]
    fn test_dimension_weights() {
        assert_eq!(HealthDimension::Documentation.weight(), 0.15);
        assert_eq!(HealthDimension::Security.weight(), 0.25);
        assert_eq!(HealthDimension::TestCoverage.weight(), 0.20);
    }

    #[test]
    fn test_project_health_computation() {
        let mut health = ProjectHealth::new("test-repo", "owner", LanguageStack::Rust);
        health.dimensions.insert(
            HealthDimension::Documentation,
            DimensionScore::new(HealthDimension::Documentation, 80.0),
        );
        health.dimensions.insert(
            HealthDimension::TestCoverage,
            DimensionScore::new(HealthDimension::TestCoverage, 90.0),
        );

        health.compute_overall_score();

        // Weighted: 80 * 0.15 + 90 * 0.20 / 0.35 = 85.7
        assert!(health.overall_score > 80.0 && health.overall_score < 90.0);
        assert_eq!(health.band, HealthBand::Good);
    }

    #[test]
    fn test_finding_creation() {
        let finding = Finding::new(
            Severity::Warning,
            HealthDimension::Documentation,
            "Missing CLAUDE.md",
        );
        assert_eq!(finding.severity, Severity::Warning);
        assert_eq!(finding.dimension, HealthDimension::Documentation);
    }
}
