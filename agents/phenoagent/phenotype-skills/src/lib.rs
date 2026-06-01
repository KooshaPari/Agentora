//! Core skill types and traits for phenotype-daemon.
//!
//! This is a local stub providing the types needed by phenotype-daemon.
//! In the full architecture, this would be generated from the Python
//! phenotype-skills package via PyO3 bindings or similar.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Errors that can occur in skill operations
#[derive(Error, Debug)]
pub enum SkillError {
    #[error("Skill not found: {0}")]
    NotFound(String),

    #[error("Skill already registered: {0}")]
    AlreadyExists(String),

    #[error("Dependency error: {0}")]
    DependencyError(String),

    #[error("Serialization error: {0}")]
    SerializationError(String),
}

impl serde::Serialize for SkillError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

/// Unique identifier for a skill
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SkillId(String);

impl SkillId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::fmt::Display for SkillId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// A skill dependency specification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillDependency {
    /// Name of the dependency
    pub name: String,
    /// Optional version constraint (e.g., ">=1.0.0")
    pub version: Option<String>,
    /// Whether this is a required dependency
    pub required: bool,
}

impl SkillDependency {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: None,
            required: true,
        }
    }

    pub fn with_version(mut self, version: impl Into<String>) -> Self {
        self.version = Some(version.into());
        self
    }

    pub fn optional(mut self) -> Self {
        self.required = false;
        self
    }
}

/// Skill manifest containing metadata and configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillManifest {
    /// Human-readable name
    pub name: String,
    /// Skill version
    pub version: String,
    /// Optional description
    pub description: Option<String>,
    /// Runtime environment requirements
    pub environment: Option<HashMap<String, String>>,
    /// Skill dependencies
    pub dependencies: Vec<SkillDependency>,
    /// Configuration schema (JSON Schema)
    pub config_schema: Option<serde_json::Value>,
}

impl SkillManifest {
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
            description: None,
            environment: None,
            dependencies: Vec::new(),
            config_schema: None,
        }
    }
}

/// Core Skill type used throughout the daemon
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    /// Unique skill identifier
    pub id: String,
    /// Skill manifest with metadata
    pub manifest: SkillManifest,
    /// Metadata about the skill instance
    pub metadata: SkillMetadata,
}

impl Skill {
    pub fn new(id: impl Into<String>, manifest: SkillManifest) -> Self {
        Self {
            id: id.into(),
            manifest,
            metadata: SkillMetadata::default(),
        }
    }
}

/// Metadata about a skill instance
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SkillMetadata {
    /// When the skill was registered
    pub registered_at: Option<String>,
    /// Who registered this skill
    pub registered_by: Option<String>,
    /// Current status
    pub status: SkillStatus,
    /// Custom labels/tags
    pub labels: HashMap<String, String>,
}

/// Skill status enum
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum SkillStatus {
    Active,
    Inactive,
    Loading,
    Error,
    #[default]
    Unknown,
}

/// Trait for skill registry operations
pub trait SkillRegistryTrait: Send + Sync {
    fn register(&mut self, skill: Skill) -> Result<(), SkillError>;
    fn unregister(&mut self, id: &SkillId) -> Result<(), SkillError>;
    fn get(&self, id: &SkillId) -> Option<&Skill>;
    fn list(&self) -> Vec<&Skill>;
    fn find_by_name(&self, name: &str) -> Vec<&Skill>;
}

/// Thread-safe skill registry
#[derive(Debug, Default)]
pub struct SkillRegistry {
    skills: dashmap::DashMap<String, Skill>,
}

impl SkillRegistry {
    pub fn new() -> Self {
        Self {
            skills: dashmap::DashMap::new(),
        }
    }

    pub fn register(&self, skill: Skill) -> Result<(), SkillError> {
        let id = skill.id.clone();
        if self.skills.contains_key(&id) {
            return Err(SkillError::AlreadyExists(id));
        }
        self.skills.insert(id, skill);
        Ok(())
    }

    pub fn unregister(&self, id: &SkillId) -> Result<(), SkillError> {
        self.skills
            .remove(id.as_str())
            .map(|_| ())
            .ok_or_else(|| SkillError::NotFound(id.to_string()))
    }

    pub fn get(&self, id: &SkillId) -> Option<Skill> {
        self.skills.get(id.as_str()).map(|v| v.clone())
    }

    pub fn list(&self) -> Vec<Skill> {
        self.skills.iter().map(|v| v.clone()).collect()
    }

    pub fn find_by_name(&self, name: &str) -> Vec<Skill> {
        self.skills
            .iter()
            .filter(|v| v.manifest.name == name)
            .map(|v| v.clone())
            .collect()
    }
}

/// Dependency resolver for skill graphs
#[derive(Debug, Default)]
pub struct DependencyResolver {
    /// Cache of resolved dependencies
    cache: std::sync::Mutex<HashMap<String, Vec<String>>>,
}

impl DependencyResolver {
    pub fn new() -> Self {
        Self {
            cache: std::sync::Mutex::new(HashMap::new()),
        }
    }

    /// Resolve all dependencies for a set of skills
    pub fn resolve(&self, skill_ids: &[SkillId], registry: &SkillRegistry) -> Vec<SkillId> {
        let mut resolved = Vec::new();
        let mut visited = std::collections::HashSet::new();

        for id in skill_ids {
            self.resolve_recursive(id, registry, &mut visited, &mut resolved);
        }

        resolved
    }

    fn resolve_recursive(
        &self,
        id: &SkillId,
        registry: &SkillRegistry,
        visited: &mut std::collections::HashSet<String>,
        resolved: &mut Vec<SkillId>,
    ) {
        if visited.contains(id.as_str()) {
            return;
        }

        visited.insert(id.to_string());

        if let Some(skill) = registry.get(id) {
            for dep in &skill.manifest.dependencies {
                let dep_id = SkillId::new(dep.name.clone());
                self.resolve_recursive(&dep_id, registry, visited, resolved);
                if !resolved.iter().any(|i| i == &dep_id) {
                    resolved.push(dep_id);
                }
            }
        }
    }

    /// Clear the resolution cache
    pub fn clear_cache(&self) {
        if let Ok(mut cache) = self.cache.lock() {
            cache.clear();
        }
    }

    /// Check for circular dependencies
    pub fn has_circular_deps(&self, skills: &[&Skill]) -> bool {
        let mut visited = std::collections::HashSet::new();
        let mut stack = Vec::new();

        for skill in skills {
            if self.detect_cycle(skill, &mut visited, &mut stack, &HashMap::new()) {
                return true;
            }
        }

        false
    }

    fn detect_cycle<'a>(
        &self,
        skill: &'a Skill,
        visited: &mut std::collections::HashSet<String>,
        stack: &mut Vec<String>,
        registry_ids: &HashMap<String, &'a Skill>,
    ) -> bool {
        let id = &skill.id;

        if stack.contains(id) {
            return true;
        }

        if visited.contains(id) {
            return false;
        }

        visited.insert(id.clone());
        stack.push(id.clone());

        for dep in &skill.manifest.dependencies {
            if self.detect_cycle_dep(&dep.name, visited, stack, registry_ids) {
                return true;
            }
        }

        stack.pop();
        false
    }

    fn detect_cycle_dep<'a>(
        &self,
        dep_name: &str,
        visited: &mut std::collections::HashSet<String>,
        stack: &mut Vec<String>,
        _registry_ids: &HashMap<String, &'a Skill>,
    ) -> bool {
        if stack.contains(&dep_name.to_string()) {
            return true;
        }

        if visited.contains(dep_name) {
            return false;
        }

        false
    }
}

// Re-export commonly used items
pub use SkillId as SkillIdentifier;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_skill_id() {
        let id = SkillId::new("test-skill");
        assert_eq!(id.as_str(), "test-skill");
        assert_eq!(id.to_string(), "test-skill");
    }

    #[test]
    fn test_skill_registry() {
        let registry = SkillRegistry::new();
        let skill = Skill::new(
            "test-1",
            SkillManifest::new("Test Skill", "1.0.0"),
        );

        assert!(registry.register(skill.clone()).is_ok());
        assert!(registry.get(&SkillId::new("test-1")).is_some());
        assert!(registry.unregister(&SkillId::new("test-1")).is_ok());
        assert!(registry.get(&SkillId::new("test-1")).is_none());
    }

    #[test]
    fn test_dependency_resolver() {
        let resolver = DependencyResolver::new();
        let registry = SkillRegistry::new();

        let mut skill = Skill::new(
            "parent",
            SkillManifest::new("Parent Skill", "1.0.0"),
        );
        skill.manifest.dependencies.push(SkillDependency::new("child"));
        registry.register(skill).unwrap();

        let child_skill = Skill::new(
            "child",
            SkillManifest::new("Child Skill", "1.0.0"),
        );
        registry.register(child_skill).unwrap();

        let resolved = resolver.resolve(&[SkillId::new("parent")], &registry);
        assert!(resolved.iter().any(|id| id.as_str() == "child"));
    }
}
