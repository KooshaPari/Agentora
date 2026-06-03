//! Declarative skill model — manifests, dependencies, and resolution.
//!
//! This module absorbs the skill *metadata* model that previously lived in the
//! vendored second runtime `crates/pheno-agent/phenotype-skills` (a self-described
//! stub). It is complementary to the behavioral [`super::Skill`] trait: the trait
//! describes how a skill *executes*, while these types describe how a skill is
//! *declared, versioned, and resolved* (dependency graph + status). Consolidating
//! both into the one `agentkit` domain removes the duplicate runtime.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::domain::{Error, Result};

/// Unique identifier for a declared skill.
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

/// A dependency of one skill on another.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillDependency {
    pub name: String,
    pub version: Option<String>,
    pub optional: bool,
}

impl SkillDependency {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: None,
            optional: false,
        }
    }
    pub fn with_version(mut self, version: impl Into<String>) -> Self {
        self.version = Some(version.into());
        self
    }
    pub fn optional(mut self) -> Self {
        self.optional = true;
        self
    }
}

/// Declarative metadata + configuration for a skill.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillManifest {
    pub name: String,
    pub version: String,
    pub description: Option<String>,
    pub environment: Option<HashMap<String, String>>,
    #[serde(default)]
    pub dependencies: Vec<SkillDependency>,
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

/// Lifecycle status of a declared skill.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum SkillStatus {
    Active,
    Inactive,
    Loading,
    Error,
    #[default]
    Unknown,
}

/// Instance metadata for a registered skill.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SkillMetadata {
    pub registered_at: Option<String>,
    pub registered_by: Option<String>,
    pub status: SkillStatus,
    pub labels: HashMap<String, String>,
}

/// A declared skill: identity + manifest + instance metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeclaredSkill {
    pub id: String,
    pub manifest: SkillManifest,
    pub metadata: SkillMetadata,
}

impl DeclaredSkill {
    pub fn new(id: impl Into<String>, manifest: SkillManifest) -> Self {
        Self {
            id: id.into(),
            manifest,
            metadata: SkillMetadata::default(),
        }
    }
}

/// Registry of declared skills (metadata catalog, distinct from the behavioral
/// [`super::SkillRegistry`] which holds executable `Box<dyn Skill>`).
#[derive(Default)]
pub struct DeclaredSkillRegistry {
    skills: HashMap<SkillId, DeclaredSkill>,
}

impl DeclaredSkillRegistry {
    pub fn new() -> Self {
        Self {
            skills: HashMap::new(),
        }
    }

    pub fn register(&mut self, skill: DeclaredSkill) -> Result<()> {
        let id = SkillId::new(skill.id.clone());
        if self.skills.contains_key(&id) {
            return Err(Error::Skill(format!("Skill '{id}' already registered")));
        }
        self.skills.insert(id, skill);
        Ok(())
    }

    pub fn unregister(&mut self, id: &SkillId) -> Result<()> {
        self.skills
            .remove(id)
            .map(|_| ())
            .ok_or_else(|| Error::Skill(format!("Skill '{id}' not found")))
    }

    pub fn get(&self, id: &SkillId) -> Option<&DeclaredSkill> {
        self.skills.get(id)
    }

    pub fn list(&self) -> Vec<&DeclaredSkill> {
        self.skills.values().collect()
    }

    pub fn find_by_name(&self, name: &str) -> Vec<&DeclaredSkill> {
        self.skills
            .values()
            .filter(|s| s.manifest.name == name)
            .collect()
    }
}

/// Resolves a declared skill's transitive dependency order and detects cycles.
#[derive(Default)]
pub struct DependencyResolver;

impl DependencyResolver {
    pub fn new() -> Self {
        Self
    }

    /// Return `skill_ids` plus their transitive dependencies, dependencies first.
    /// Unknown dependency names are skipped (treated as externally provided).
    pub fn resolve(&self, skill_ids: &[SkillId], registry: &DeclaredSkillRegistry) -> Vec<SkillId> {
        let mut ordered: Vec<SkillId> = Vec::new();
        let mut seen: std::collections::HashSet<SkillId> = std::collections::HashSet::new();

        fn visit(
            id: &SkillId,
            registry: &DeclaredSkillRegistry,
            seen: &mut std::collections::HashSet<SkillId>,
            ordered: &mut Vec<SkillId>,
        ) {
            if seen.contains(id) {
                return;
            }
            seen.insert(id.clone());
            if let Some(skill) = registry.get(id) {
                for dep in &skill.manifest.dependencies {
                    let dep_id = SkillId::new(dep.name.clone());
                    if registry.get(&dep_id).is_some() {
                        visit(&dep_id, registry, seen, ordered);
                    }
                }
            }
            ordered.push(id.clone());
        }

        for id in skill_ids {
            visit(id, registry, &mut seen, &mut ordered);
        }
        ordered
    }

    /// Detect a circular dependency among the supplied declared skills.
    pub fn has_circular_deps(&self, skills: &[&DeclaredSkill]) -> bool {
        let by_name: HashMap<&str, &DeclaredSkill> = skills
            .iter()
            .map(|s| (s.manifest.name.as_str(), *s))
            .collect();

        #[derive(Clone, Copy, PartialEq)]
        enum Mark {
            Visiting,
            Done,
        }
        let mut marks: HashMap<&str, Mark> = HashMap::new();

        fn dfs<'a>(
            name: &'a str,
            by_name: &HashMap<&'a str, &'a DeclaredSkill>,
            marks: &mut HashMap<&'a str, Mark>,
        ) -> bool {
            match marks.get(name) {
                Some(Mark::Visiting) => return true,
                Some(Mark::Done) => return false,
                None => {}
            }
            marks.insert(name, Mark::Visiting);
            if let Some(skill) = by_name.get(name) {
                for dep in &skill.manifest.dependencies {
                    if let Some((dep_name, _)) = by_name.get_key_value(dep.name.as_str()) {
                        if dfs(dep_name, by_name, marks) {
                            return true;
                        }
                    }
                }
            }
            marks.insert(name, Mark::Done);
            false
        }

        by_name.keys().any(|n| dfs(n, &by_name, &mut marks))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn skill(name: &str, deps: &[&str]) -> DeclaredSkill {
        let mut m = SkillManifest::new(name, "0.1.0");
        m.dependencies = deps.iter().map(|d| SkillDependency::new(*d)).collect();
        DeclaredSkill::new(name, m)
    }

    #[test]
    fn register_and_lookup() {
        let mut reg = DeclaredSkillRegistry::new();
        reg.register(skill("a", &[])).unwrap();
        assert!(reg.register(skill("a", &[])).is_err(), "duplicate rejected");
        assert_eq!(reg.find_by_name("a").len(), 1);
        assert_eq!(reg.list().len(), 1);
    }

    #[test]
    fn resolve_orders_dependencies_first() {
        let mut reg = DeclaredSkillRegistry::new();
        reg.register(skill("base", &[])).unwrap();
        reg.register(skill("app", &["base"])).unwrap();
        let order = DependencyResolver::new().resolve(&[SkillId::new("app")], &reg);
        let base = order.iter().position(|i| i.as_str() == "base").unwrap();
        let app = order.iter().position(|i| i.as_str() == "app").unwrap();
        assert!(base < app, "dependency must come before dependent");
    }

    #[test]
    fn detects_circular_dependencies() {
        let a = skill("a", &["b"]);
        let b = skill("b", &["a"]);
        assert!(DependencyResolver::new().has_circular_deps(&[&a, &b]));
        let x = skill("x", &[]);
        let y = skill("y", &["x"]);
        assert!(!DependencyResolver::new().has_circular_deps(&[&x, &y]));
    }
}
