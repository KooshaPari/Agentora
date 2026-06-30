//! Substrate-backed [`SkillRegistry`] adapter.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use serde_json::Value;
use substrate::skill_port::{SkillDescriptor, SkillHandler};
use substrate::ToolRegistry as SubstrateToolRegistry;

use crate::adapters::substrate::InMemorySkillRegistry;
use crate::domain::skills::Skill;
use crate::domain::{Error, Result};

struct SkillHandlerBridge {
    skill: Arc<dyn Skill>,
}

impl SkillHandler for SkillHandlerBridge {
    fn invoke(&self, input: Value) -> substrate::Result<Value> {
        let skill = self.skill.clone();
        let result = tokio::task::block_in_place(move || {
            tokio::runtime::Handle::current().block_on(skill.execute(input))
        })
        .map_err(|e| substrate::SubstrateError::Other(e.to_string()))?;
        if result.success {
            Ok(result.data)
        } else {
            Err(substrate::SubstrateError::Other(
                result.error.unwrap_or_else(|| "skill failed".into()),
            ))
        }
    }
}

/// Skill registry — substrate [`SkillPort`] dispatch.
pub struct SkillRegistry {
    inner: Mutex<InMemorySkillRegistry>,
    skills: HashMap<String, Arc<dyn Skill>>,
}

impl SkillRegistry {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(InMemorySkillRegistry::new()),
            skills: HashMap::new(),
        }
    }

    pub fn register(&mut self, skill: Box<dyn Skill>) -> Result<()> {
        let skill: Arc<dyn Skill> = Arc::from(skill);
        let name = skill.name().to_string();
        if self.skills.contains_key(&name) {
            return Err(Error::Skill(format!("Skill '{name}' already registered")));
        }
        let descriptor = SkillDescriptor {
            name: name.clone(),
            description: skill.description(),
            input_schema: serde_json::json!({
                "type": "object",
                "properties": {},
                "required": []
            }),
            output_schema: serde_json::json!({ "type": "object" }),
        };
        SubstrateToolRegistry::register(
            &mut *self.inner.lock().unwrap_or_else(|e| e.into_inner()),
            descriptor,
            Box::new(SkillHandlerBridge {
                skill: skill.clone(),
            }),
        )
        .map_err(|e| Error::Skill(e.to_string()))?;
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
