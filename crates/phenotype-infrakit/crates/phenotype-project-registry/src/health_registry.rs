//! Health Dashboard Registry
//!
//! Aggregates health dashboard configurations from all projects and provides
//! a unified view of project health across the Phenotype ecosystem.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tokio::fs;

/// Health Dashboard Configuration loaded from .health-dashboard.yml
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthDashboardConfig {
    pub project: ProjectInfo,
    pub dimensions: Dimensions,
    pub alerts: Alerts,
    pub integration: Integration,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub name: String,
    pub language: String,
    pub description: String,
    pub tier: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dimensions {
    pub documentation: Dimension,
    pub test_coverage: Dimension,
    pub security: Dimension,
    pub dependencies: Dimension,
    pub compliance: Dimension,
    pub code_quality: Dimension,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dimension {
    pub weight: u8,
    #[serde(default)]
    pub files: Vec<String>,
    #[serde(default)]
    pub thresholds: Option<Thresholds>,
    #[serde(default)]
    pub scanners: Vec<String>,
    #[serde(default)]
    pub required_files: Vec<String>,
    #[serde(default)]
    pub linters: Vec<String>,
    #[serde(default)]
    pub track_missing: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Thresholds {
    pub min_line_coverage: u8,
    pub min_branch_coverage: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alerts {
    pub critical_threshold: u8,
    pub poor_threshold: u8,
    pub frequency_hours: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Integration {
    #[serde(default)]
    pub github_repo: Option<String>,
    #[serde(default)]
    pub codecov_repo: Option<String>,
    #[serde(default)]
    pub snyk_org: Option<String>,
}

/// Registry of all health dashboard configurations
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HealthDashboardRegistry {
    pub projects: HashMap<String, ProjectHealthEntry>,
    pub last_scan: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectHealthEntry {
    pub name: String,
    pub path: PathBuf,
    pub language: String,
    pub tier: String,
    pub has_config: bool,
    pub config: Option<HealthDashboardConfig>,
    pub missing_files: Vec<String>,
}

impl HealthDashboardRegistry {
    /// Discover health dashboard configurations in the given root directory
    pub async fn discover_in(root: &Path) -> anyhow::Result<Self> {
        let mut registry = Self::default();
        registry.last_scan = chrono::Utc::now();

        let mut entries = fs::read_dir(root).await?;

        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            if path.is_dir() {
                let config_path = path.join(".health-dashboard.yml");
                if config_path.exists() {
                    match Self::load_config(&config_path).await {
                        Ok(config) => {
                            let missing = Self::check_missing_files(&path, &config);
                            registry.projects.insert(
                                config.project.name.clone(),
                                ProjectHealthEntry {
                                    name: config.project.name.clone(),
                                    path: path.clone(),
                                    language: config.project.language.clone(),
                                    tier: config.project.tier.clone(),
                                    has_config: true,
                                    config: Some(config),
                                    missing_files: missing,
                                },
                            );
                        }
                        Err(e) => {
                            tracing::warn!("Failed to load config from {}: {}", config_path.display(), e);
                        }
                    }
                }
            }
        }

        Ok(registry)
    }

    async fn load_config(path: &Path) -> anyhow::Result<HealthDashboardConfig> {
        let content = fs::read_to_string(path).await?;
        let config: HealthDashboardConfig = serde_yaml_ng::from_str(&content)?;
        Ok(config)
    }

    fn check_missing_files(path: &Path, config: &HealthDashboardConfig) -> Vec<String> {
        let mut missing = Vec::new();

        for file in &config.dimensions.documentation.files {
            if !path.join(file).exists() {
                missing.push(file.clone());
            }
        }

        for file in &config.dimensions.compliance.required_files {
            if !path.join(file).exists() {
                missing.push(file.clone());
            }
        }

        missing
    }

    pub fn len(&self) -> usize {
        self.projects.len()
    }

    pub fn is_empty(&self) -> bool {
        self.projects.is_empty()
    }

    pub fn summary(&self) -> HealthRegistrySummary {
        let total = self.projects.len();
        if total == 0 {
            return HealthRegistrySummary::default();
        }

        let mut tier1 = 0;
        let mut tier2 = 0;
        let mut with_configs = 0;
        let mut total_missing = 0;

        for entry in self.projects.values() {
            match entry.tier.as_str() {
                "tier1" => tier1 += 1,
                "tier2" => tier2 += 1,
                _ => {}
            }
            if entry.has_config {
                with_configs += 1;
            }
            total_missing += entry.missing_files.len();
        }

        HealthRegistrySummary {
            total_projects: total,
            tier1_projects: tier1,
            tier2_projects: tier2,
            with_health_configs: with_configs,
            total_missing_files: total_missing,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HealthRegistrySummary {
    pub total_projects: usize,
    pub tier1_projects: usize,
    pub tier2_projects: usize,
    pub with_health_configs: usize,
    pub total_missing_files: usize,
}
