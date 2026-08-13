//! Substrate-backed [`ToolRegistry`] adapter.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use serde_json::Value;
use substrate::skill_port::{SkillDescriptor, SkillHandler, SkillPort};
use substrate::ToolRegistry as SubstrateToolRegistry;

use crate::adapters::substrate::InMemorySkillRegistry;
use crate::domain::ports::ToolExecutor;
use crate::domain::tools::{Tool, ToolCall, ToolResponse};
use crate::domain::{Error, Result};

struct ToolHandler {
    tool: Arc<dyn Tool>,
}

impl SkillHandler for ToolHandler {
    fn invoke(&self, input: Value) -> substrate::Result<Value> {
        let tool = self.tool.clone();
        let call = ToolCall::new(tool.name(), input, "invoke");
        tokio::task::block_in_place(move || {
            tokio::runtime::Handle::current().block_on(tool.call(call))
        })
        .map_err(|e| substrate::SubstrateError::Other(e.to_string()))
    }
}

/// Tool registry — substrate [`SkillPort`] dispatch.
pub struct ToolRegistry {
    inner: Mutex<InMemorySkillRegistry>,
    tools: HashMap<String, Arc<dyn Tool>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(InMemorySkillRegistry::new()),
            tools: HashMap::new(),
        }
    }

    pub fn register(&mut self, tool: Box<dyn Tool>) -> Result<()> {
        let tool: Arc<dyn Tool> = Arc::from(tool);
        let name = tool.name().to_string();
        if self.tools.contains_key(&name) {
            return Err(Error::Tool(format!("Tool '{name}' already registered")));
        }
        let descriptor = SkillDescriptor {
            name: name.clone(),
            description: tool.description(),
            input_schema: tool.parameters(),
            output_schema: serde_json::json!({ "type": "object" }),
        };
        SubstrateToolRegistry::register(
            &mut *self
                .inner
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
            descriptor,
            Box::new(ToolHandler { tool: tool.clone() }),
        )
        .map_err(|e| Error::Tool(e.to_string()))?;
        self.tools.insert(name, tool);
        Ok(())
    }

    pub fn get(&self, name: &str) -> Option<&dyn Tool> {
        self.tools.get(name).map(AsRef::as_ref)
    }

    pub fn list(&self) -> Vec<&str> {
        self.tools.keys().map(String::as_str).collect()
    }

    pub fn has(&self, name: &str) -> bool {
        self.tools.contains_key(name)
    }

    pub fn call(&self, call: ToolCall) -> Result<ToolResponse> {
        if !self.has(&call.name) {
            return Err(Error::Tool(format!("Tool '{}' not found", call.name)));
        }
        let id = call.id.clone();
        let name = call.name.clone();
        let registry = self
            .inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let invocation = SkillPort::invoke(&*registry, &name, call.params);
        drop(registry);
        match invocation {
            Ok(result) => Ok(ToolResponse::success(id, result)),
            Err(e) => Ok(ToolResponse::failure(id, e.to_string())),
        }
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ToolExecutor for ToolRegistry {
    async fn execute(&self, call: ToolCall) -> Result<ToolResponse> {
        self.call(call)
    }
}
