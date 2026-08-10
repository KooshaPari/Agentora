//! Skill domain - Modular agent capabilities

use crate::domain::{Error, Result};
use async_trait::async_trait;
use serde_json::Value;

/// Skill trait - implement this to create a skill
#[async_trait]
pub trait Skill: Send + Sync {
    fn name(&self) -> &str;

    fn description(&self) -> String {
        String::new()
    }

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

/// Built-in skill for web search (placeholder)
pub struct WebSearchSkill;

#[async_trait]
impl Skill for WebSearchSkill {
    fn name(&self) -> &'static str {
        "web_search"
    }

    fn description(&self) -> String {
        "Search the web for information".to_string()
    }

    async fn execute(&self, params: Value) -> Result<SkillResult> {
        let query = params
            .get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| Error::Skill("Missing 'query' parameter".to_string()))?;

        Ok(SkillResult::success(serde_json::json!({
            "query": query,
            "results": []
        })))
    }
}
