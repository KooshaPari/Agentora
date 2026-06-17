//! In-memory skill/tool registry backed by substrate [`ToolRegistry`] + [`SkillPort`].

use std::collections::HashMap;

use substrate::skill_port::{
    validate_json_schema, SkillDescriptor, SkillHandler, SkillPort, ToolRegistry,
};
use substrate::{SubstrateError, Result as SubstrateResult};

/// In-memory registry implementing substrate skill/tool ports.
#[derive(Default)]
pub struct InMemorySkillRegistry {
    entries: HashMap<String, (SkillDescriptor, Box<dyn SkillHandler>)>,
}

impl InMemorySkillRegistry {
    pub fn new() -> Self {
        Self::default()
    }
}

impl ToolRegistry for InMemorySkillRegistry {
    fn register(
        &mut self,
        descriptor: SkillDescriptor,
        handler: Box<dyn SkillHandler>,
    ) -> SubstrateResult<()> {
        if self.entries.contains_key(&descriptor.name) {
            return Err(SubstrateError::Other(format!(
                "already registered: {}",
                descriptor.name
            )));
        }
        if !descriptor.input_schema.is_object() || !descriptor.output_schema.is_object() {
            return Err(SubstrateError::SchemaValidation(
                "input_schema and output_schema must be JSON objects".into(),
            ));
        }
        self.entries
            .insert(descriptor.name.clone(), (descriptor, handler));
        Ok(())
    }

    fn lookup(&self, name: &str) -> Option<&SkillDescriptor> {
        self.entries.get(name).map(|(d, _)| d)
    }

    fn list(&self) -> Vec<SkillDescriptor> {
        self.entries.values().map(|(d, _)| d.clone()).collect()
    }

    fn validate_input(&self, name: &str, input: &serde_json::Value) -> SubstrateResult<()> {
        let descriptor = self
            .lookup(name)
            .ok_or_else(|| SubstrateError::NotFound(format!("skill not found: {name}")))?;
        validate_json_schema(input, &descriptor.input_schema)
    }
}

impl SkillPort for InMemorySkillRegistry {
    fn invoke(&self, name: &str, input: serde_json::Value) -> SubstrateResult<serde_json::Value> {
        self.validate_input(name, &input)?;
        let handler = self
            .entries
            .get(name)
            .ok_or_else(|| SubstrateError::NotFound(format!("skill not found: {name}")))?;
        handler.1.invoke(input)
    }

    fn list_skills(&self) -> Vec<SkillDescriptor> {
        self.list()
    }
}
