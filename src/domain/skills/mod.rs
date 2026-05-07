//! Skill domain - Modular agent capabilities

use async_trait::async_trait;
use serde_json::Value;
use std::collections::HashMap;
use crate::domain::{Result, Error};

/// Skill trait - implement this to create a skill
#[async_trait]
pub trait Skill: Send + Sync {
    /// Get skill name
    fn name(&self) -> &str;

    /// Get skill description
    fn description(&self) -> String {
        String::new()
    }

    /// Execute the skill
    async fn execute(&self, params: Value) -> Result<SkillResult>;
}

/// Skill result
#[derive(Debug, Clone)]
pub struct SkillResult {
    pub success: bool,
    pub data: Value,
    pub error: Option<String>,
}

impl SkillResult {
    pub fn success(data: Value) -> Self {
        Self {
            success: true,
            data,
            error: None,
        }
    }

    pub fn failure(error: impl Into<String>) -> Self {
        Self {
            success: false,
            data: Value::Null,
            error: Some(error.into()),
        }
    }
}

/// Skill registry - manages available skills
pub struct SkillRegistry {
    skills: HashMap<String, Box<dyn Skill>>,
}

impl SkillRegistry {
    pub fn new() -> Self {
        Self {
            skills: HashMap::new(),
        }
    }

    pub fn register(&mut self, skill: Box<dyn Skill>) -> Result<()> {
        let name = skill.name().to_string();
        if self.skills.contains_key(&name) {
            return Err(Error::Skill(format!("Skill '{}' already registered", name)));
        }
        self.skills.insert(name, skill);
        Ok(())
    }

    pub fn get(&self, name: &str) -> Option<&dyn Skill> {
        self.skills.get(name).map(|s| s.as_ref())
    }

    pub fn list(&self) -> Vec<&str> {
        self.skills.keys().map(|s| s.as_str()).collect()
    }

    pub fn has(&self, name: &str) -> bool {
        self.skills.contains_key(name)
    }
}

impl Default for SkillRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Built-in skill for web search (placeholder)
pub struct WebSearchSkill;

#[async_trait]
impl Skill for WebSearchSkill {
    fn name(&self) -> &str {
        "web_search"
    }

    fn description(&self) -> String {
        "Search the web for information".to_string()
    }

    async fn execute(&self, params: Value) -> Result<SkillResult> {
        let query = params.get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| Error::Skill("Missing 'query' parameter".to_string()))?;

        // Placeholder - implement actual search
        Ok(SkillResult::success(serde_json::json!({
            "query": query,
            "results": []
        })))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_skill_registry() {
        let mut registry = SkillRegistry::new();

        registry.register(Box::new(WebSearchSkill))
            .expect("Failed to register skill");

        assert!(registry.has("web_search"));
        assert_eq!(registry.list(), vec!["web_search"]);
    }
}
