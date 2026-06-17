//! Tool domain - Extensible tool system

use crate::domain::{Error, Result};
use async_trait::async_trait;
use serde_json::Value;

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
    fn name(&self) -> &str;

    fn description(&self) -> String {
        String::new()
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {},
            "required": []
        })
    }

    async fn call(&self, call: ToolCall) -> Result<Value>;
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
        let expr = call
            .params
            .get("expression")
            .and_then(|v| v.as_str())
            .ok_or_else(|| Error::Tool("Missing 'expression' parameter".to_string()))?;

        if expr.is_empty() {
            return Err(Error::Tool("Expression cannot be empty".to_string()));
        }
        if expr.len() > 1024 {
            return Err(Error::Tool(
                "Expression too long (max 1024 chars)".to_string(),
            ));
        }

        Ok(serde_json::json!({
            "expression": expr,
            "result": 0.0
        }))
    }
}
