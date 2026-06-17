//! Project registry for Phenotype
//!
//! Provides project metadata management and discovery.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Project metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub id: String,
    pub name: String,
    pub description: String,
    pub version: String,
    pub path: String,
    pub tags: Vec<String>,
    pub metadata: HashMap<String, String>,
}

impl Project {
    /// Create a new project
    pub fn new(id: impl Into<String>, name: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            description: String::new(),
            version: "0.1.0".to_string(),
            path: String::new(),
            tags: Vec::new(),
            metadata: HashMap::new(),
        }
    }
    
    /// Set description
    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = desc.into();
        self
    }
    
    /// Set version
    pub fn with_version(mut self, version: impl Into<String>) -> Self {
        self.version = version.into();
        self
    }
    
    /// Set path
    pub fn with_path(mut self, path: impl Into<String>) -> Self {
        self.path = path.into();
        self
    }
    
    /// Add a tag
    pub fn with_tag(mut self, tag: impl Into<String>) -> Self {
        self.tags.push(tag.into());
        self
    }
    
    /// Add metadata
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }
}

/// Registry of projects
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct ProjectRegistry {
    projects: HashMap<String, Project>,
}

impl ProjectRegistry {
    /// Create a new empty registry
    pub fn new() -> Self {
        Self {
            projects: HashMap::new(),
        }
    }
    
    /// Register a project
    pub fn register(&mut self, project: Project) {
        self.projects.insert(project.id.clone(), project);
    }
    
    /// Get a project by ID
    pub fn get(&self, id: &str) -> Option<&Project> {
        self.projects.get(id)
    }
    
    /// Remove a project
    pub fn remove(&mut self, id: &str) -> Option<Project> {
        self.projects.remove(id)
    }
    
    /// List all projects
    pub fn list(&self) -> Vec<&Project> {
        self.projects.values().collect()
    }
    
    /// Find projects by tag
    pub fn find_by_tag(&self, tag: &str) -> Vec<&Project> {
        self.projects
            .values()
            .filter(|p| p.tags.contains(&tag.to_string()))
            .collect()
    }
    
    /// Search projects by name
    pub fn search(&self, query: &str) -> Vec<&Project> {
        let query = query.to_lowercase();
        self.projects
            .values()
            .filter(|p| {
                p.name.to_lowercase().contains(&query) ||
                p.description.to_lowercase().contains(&query)
            })
            .collect()
    }
    
    /// Get project count
    pub fn count(&self) -> usize {
        self.projects.len()
    }
    
    /// Load from JSON
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }
    
    /// Save to JSON
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
}

/// Registry builder
#[derive(Debug, Default)]
pub struct RegistryBuilder {
    registry: ProjectRegistry,
}

impl RegistryBuilder {
    /// Create a new builder
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Add a project
    pub fn with_project(mut self, project: Project) -> Self {
        self.registry.register(project);
        self
    }
    
    /// Build the registry
    pub fn build(self) -> ProjectRegistry {
        self.registry
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_project_builder() {
        let project = Project::new("p1", "Test Project")
            .with_description("A test project")
            .with_version("1.0.0")
            .with_tag("test");
        
        assert_eq!(project.id, "p1");
        assert_eq!(project.name, "Test Project");
        assert!(project.tags.contains("test"));
    }

    #[test]
    fn test_registry() {
        let mut registry = ProjectRegistry::new();
        let project = Project::new("p1", "Test");
        
        registry.register(project);
        assert_eq!(registry.count(), 1);
        assert!(registry.get("p1").is_some());
    }

    #[test]
    fn test_search() {
        let registry = RegistryBuilder::new()
            .with_project(Project::new("p1", "Alpha"))
            .with_project(Project::new("p2", "Beta"))
            .build();
        
        let results = registry.search("alpha");
        assert_eq!(results.len(), 1);
    }
}
