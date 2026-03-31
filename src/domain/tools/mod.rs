//! Tool domain - Extensible tool system

use async_trait::async_trait;
use serde_json::Value;
use std::collections::HashMap;
use crate::domain::{Result, Error};

/// Tool call request
#[derive(Debug, Clone)]
pub struct ToolCall {
    pub name: String,
    pub params: Value,
    pub id: String,
}

impl ToolCall {
    pub fn new(name: impl Into<String>, params: Value, id: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            params,
            id: id.into(),
        }
    }
}

/// Tool response
#[derive(Debug, Clone)]
pub struct ToolResponse {
    pub id: String,
    pub result: Value,
    pub error: Option<String>,
}

impl ToolResponse {
    pub fn success(id: impl Into<String>, result: Value) -> Self {
        Self {
            id: id.into(),
            result,
            error: None,
        }
    }

    pub fn failure(id: impl Into<String>, error: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            result: Value::Null,
            error: Some(error.into()),
        }
    }
}

/// Tool trait - implement this to create a tool
#[async_trait]
pub trait Tool: Send + Sync {
    /// Get tool name
    fn name(&self) -> &str;

    /// Get tool description
    fn description(&self) -> String {
        String::new()
    }

    /// Get parameter schema
    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {},
            "required": []
        })
    }

    /// Execute the tool
    async fn call(&self, call: ToolCall) -> Result<Value>;
}

/// Tool registry - manages available tools
pub struct ToolRegistry {
    tools: HashMap<String, Box<dyn Tool>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
        }
    }

    pub fn register(&mut self, tool: Box<dyn Tool>) -> Result<()> {
        let name = tool.name().to_string();
        if self.tools.contains_key(&name) {
            return Err(Error::Tool(format!("Tool '{}' already registered", name)));
        }
        self.tools.insert(name, tool);
        Ok(())
    }

    pub fn get(&self, name: &str) -> Option<&dyn Tool> {
        self.tools.get(name).map(|t| t.as_ref())
    }

    pub fn list(&self) -> Vec<&str> {
        self.tools.keys().map(|s| s.as_str()).collect()
    }

    pub fn has(&self, name: &str) -> bool {
        self.tools.contains_key(name)
    }

    pub async fn call(&self, call: ToolCall) -> Result<ToolResponse> {
        let tool = self.tools.get(&call.name)
            .ok_or_else(|| Error::Tool(format!("Tool '{}' not found", call.name)))?;

        match tool.call(call.clone()).await {
            Ok(result) => Ok(ToolResponse::success(call.id, result)),
            Err(e) => Ok(ToolResponse::failure(call.id, e.to_string())),
        }
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Calculator tool
pub struct CalculatorTool;

#[async_trait]
impl Tool for CalculatorTool {
    fn name(&self) -> &str {
        "calculator"
    }

    fn description(&self) -> String {
        "Evaluate mathematical expressions".to_string()
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        })
    }

    async fn call(&self, call: ToolCall) -> Result<Value> {
        let expr = call.params.get("expression")
            .and_then(|v| v.as_str())
            .ok_or_else(|| Error::Tool("Missing 'expression' parameter".to_string()))?;

        // Validate input: reject empty expressions and excessively long input
        if expr.is_empty() {
            return Err(Error::Tool("Expression cannot be empty".to_string()));
        }
        if expr.len() > 1024 {
            return Err(Error::Tool("Expression too long (max 1024 chars)".to_string()));
        }

        // Placeholder implementation - returns 0.0 for all expressions
        // TODO: implement a safe expression parser (never use eval/shell execution)
        Ok(serde_json::json!({
            "expression": expr,
            "result": 0.0 // Placeholder
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_tool_registry() {
        let mut registry = ToolRegistry::new();

        registry.register(Box::new(CalculatorTool))
            .expect("Failed to register tool");

        assert!(registry.has("calculator"));
    }
}
