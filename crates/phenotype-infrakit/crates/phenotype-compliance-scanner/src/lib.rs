//! Documentation and Compliance Scanner
//!
//! Scans projects for documentation completeness and governance file presence.
//! Used by the unified health dashboard to track project compliance.
//!
//! # Features
//!
//! - Documentation file scanning (CLAUDE.md, README.md, CONTRIBUTING.md, etc.)
//! - Governance file checking (deny.toml, codecov.yml, .pre-commit-config.yaml)
//! - Freshness tracking (90-day threshold for documentation updates)
//! - Compliance scoring

use crate::project::{DimensionScore, Finding, HealthDimension, Severity};
use chrono::{DateTime, Duration, Utc};
use std::path::Path;
use tokio::fs;

/// Documentation file names to check
const REQUIRED_DOCS: &[&str] = &[
    "CLAUDE.md",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "CHANGELOG.md",
];

/// Required governance files
const REQUIRED_GOVERNANCE: &[&str] = &[
    "deny.toml",
    "codecov.yml",
    ".pre-commit-config.yaml",
    ".github/workflows/ci.yml",
    ".github/workflows/security.yml",
];

/// Documentation scanner result
#[derive(Debug, Clone)]
pub struct DocumentationScanResult {
    pub score: f32,
    pub present_files: Vec<String>,
    pub missing_files: Vec<String>,
    pub stale_files: Vec<String>,
    pub findings: Vec<Finding>,
}

/// Governance scanner result
#[derive(Debug, Clone)]
pub struct GovernanceScanResult {
    pub score: f32,
    pub present_files: Vec<String>,
    pub missing_files: Vec<String>,
    pub findings: Vec<Finding>,
}

/// Documentation and Governance Scanner
#[derive(Debug, Clone, Default)]
pub struct DocumentationScanner {
    freshness_threshold_days: i64,
}

impl DocumentationScanner {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_freshness_threshold(mut self, days: i64) -> Self {
        self.freshness_threshold_days = days;
        self
    }

    /// Scan a project directory for documentation files
    pub async fn scan_documentation(&self, path: &Path) -> DocumentationScanResult {
        let mut present = Vec::new();
        let mut missing = Vec::new();
        let mut stale = Vec::new();
        let mut findings = Vec::new();

        for doc in REQUIRED_DOCS {
            let doc_path = path.join(doc);
            if doc_path.exists() {
                present.push(doc.to_string());

                // Check freshness
                if let Ok(metadata) = fs::metadata(&doc_path).await {
                    if let Ok(modified) = metadata.modified() {
                        let modified: DateTime<Utc> = modified.into();
                        let age = Utc::now() - modified;
                        if age > Duration::days(self.freshness_threshold_days) {
                            stale.push(doc.to_string());
                            findings.push(Finding::new(
                                Severity::Warning,
                                HealthDimension::Documentation,
                                format!("{} is older than {} days", doc, self.freshness_threshold_days),
                            ));
                        }
                    }
                }
            } else {
                missing.push(doc.to_string());
                findings.push(Finding::new(
                    Severity::Error,
                    HealthDimension::Documentation,
                    format!("Missing required documentation: {}", doc),
                ));
            }
        }

        let total = REQUIRED_DOCS.len() as f32;
        let present_count = present.len() as f32;
        let score = (present_count / total) * 100.0;

        DocumentationScanResult {
            score,
            present_files: present,
            missing_files: missing,
            stale_files: stale,
            findings,
        }
    }

    /// Scan a project directory for governance files
    pub async fn scan_governance(&self, path: &Path) -> GovernanceScanResult {
        let mut present = Vec::new();
        let mut missing = Vec::new();
        let mut findings = Vec::new();

        for gov in REQUIRED_GOVERNANCE {
            let gov_path = path.join(gov);
            if gov_path.exists() {
                present.push(gov.to_string());
            } else {
                missing.push(gov.to_string());
                findings.push(Finding::new(
                    Severity::Warning,
                    HealthDimension::Compliance,
                    format!("Missing governance file: {}", gov),
                ));
            }
        }

        let total = REQUIRED_GOVERNANCE.len() as f32;
        let present_count = present.len() as f32;
        let score = (present_count / total) * 100.0;

        GovernanceScanResult {
            score,
            present_files: present,
            missing_files: missing,
            findings,
        }
    }

    /// Get compliance score as a percentage
    pub fn compliance_score(&self, doc: &DocumentationScanResult, gov: &GovernanceScanResult) -> f32 {
        (doc.score * 0.5 + gov.score * 0.5)
    }
}

/// Scan a complete project and return combined results
pub async fn scan_project(path: &Path) -> (DocumentationScanResult, GovernanceScanResult) {
    let scanner = DocumentationScanner::new();
    let doc_result = scanner.scan_documentation(path).await;
    let gov_result = scanner.scan_governance(path).await;
    (doc_result, gov_result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_scanner() {
        let scanner = DocumentationScanner::new();
        let temp = TempDir::new().unwrap();

        let result = scanner.scan_documentation(temp.path()).await;
        assert_eq!(result.score, 0.0);
        assert_eq!(result.missing_files.len(), REQUIRED_DOCS.len());
    }

    #[tokio::test]
    async fn test_documentation_scanner_empty() {
        let temp = TempDir::new().unwrap();
        let scanner = DocumentationScanner::new();

        let doc_result = scanner.scan_documentation(temp.path()).await;
        assert_eq!(doc_result.score, 0.0);
        assert!(doc_result.missing_files.contains(&"CLAUDE.md".to_string()));
    }

    #[tokio::test]
    async fn test_documentation_scanner_complete() {
        let temp = TempDir::new().unwrap();

        // Create all required documentation files
        for doc in REQUIRED_DOCS {
            let _ = fs::write(temp.path().join(doc), "# Test").await;
        }

        let scanner = DocumentationScanner::new();
        let doc_result = scanner.scan_documentation(temp.path()).await;

        assert_eq!(doc_result.score, 100.0);
        assert!(doc_result.missing_files.is_empty());
    }
}
