//! Project Discovery Module
//!
//! Discovers projects in the file system and extracts metadata.

use std::path::{Path, PathBuf};
use tokio::fs;
use walkdir::WalkDir;

/// Project type based on language
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectType {
    Rust,
    TypeScript,
    Python,
    Go,
    Unknown,
}

impl ProjectType {
    pub fn from_path(path: &Path) -> Self {
        if path.join("Cargo.toml").exists() {
            return ProjectType::Rust;
        }
        if path.join("package.json").exists() {
            return ProjectType::TypeScript;
        }
        if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
            return ProjectType::Python;
        }
        if path.join("go.mod").exists() {
            return ProjectType::Go;
        }
        ProjectType::Unknown
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            ProjectType::Rust => "rust",
            ProjectType::TypeScript => "typescript",
            ProjectType::Python => "python",
            ProjectType::Go => "go",
            ProjectType::Unknown => "unknown",
        }
    }
}

/// Discovered project metadata
#[derive(Debug, Clone)]
pub struct Project {
    pub name: String,
    pub path: PathBuf,
    pub project_type: ProjectType,
    pub has_github_workflows: bool,
    pub has_codecov: bool,
    pub has_claude_md: bool,
}

impl Project {
    pub fn new(name: String, path: PathBuf, project_type: ProjectType) -> Self {
        Self {
            name,
            path: path.clone(),
            project_type,
            has_github_workflows: path.join(".github/workflows").exists(),
            has_codecov: path.join("codecov.yml").exists(),
            has_claude_md: path.join("CLAUDE.md").exists(),
        }
    }
}

/// Project registry - collection of discovered projects
#[derive(Debug, Clone, Default)]
pub struct ProjectRegistry {
    pub projects: Vec<Project>,
}

impl ProjectRegistry {
    /// Discover all projects in the given root directory.
    pub async fn discover(root: &Path) -> anyhow::Result<Self> {
        let mut registry = Self::default();

        let mut entries = fs::read_dir(root).await?;

        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            if path.is_dir() {
                // Skip hidden directories and special directories
                let name = path.file_name()
                    .map(|n| n.to_string_lossy().to_string())
                    .unwrap_or_default();

                if name.starts_with('.') || name == "target" || name == "node_modules" {
                    continue;
                }

                let project_type = ProjectType::from_path(&path);
                if project_type != ProjectType::Unknown {
                    registry.projects.push(Project::new(name, path, project_type));
                }
            }
        }

        Ok(registry)
    }

    /// Get projects filtered by type.
    pub fn by_type(&self, project_type: &ProjectType) -> Vec<&Project> {
        self.projects.iter()
            .filter(|p| &p.project_type == project_type)
            .collect()
    }

    /// Get count of projects by type.
    pub fn count_by_type(&self) -> std::collections::HashMap<ProjectType, usize> {
        let mut counts = std::collections::HashMap::new();
        for project in &self.projects {
            *counts.entry(project.project_type.clone()).or_insert(0) += 1;
        }
        counts
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_discover_rust_project() {
        let temp = TempDir::new().unwrap();
        let project_dir = temp.path().join("my-project");
        fs::create_dir(&project_dir).await.unwrap();
        fs::write(project_dir.join("Cargo.toml"), "[package]\nname = \"test\"").await.unwrap();

        let registry = ProjectRegistry::discover(temp.path()).await.unwrap();
        assert_eq!(registry.projects.len(), 1);
        assert_eq!(registry.projects[0].project_type, ProjectType::Rust);
    }

    #[tokio::test]
    async fn test_empty_registry() {
        let temp = TempDir::new().unwrap();
        let registry = ProjectRegistry::discover(temp.path()).await.unwrap();
        assert_eq!(registry.projects.len(), 0);
    }
}
