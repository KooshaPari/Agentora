//! FR-003 acceptance tests: Tool registry with JSON-schema parameters and
//! tool dispatch.
//!
//! Each `#[test]` in this module is annotated with the FR it exercises.
//! FR-003: tool registry

use agentkit::domain::tools::{CalculatorTool, Tool, ToolCall};
use agentkit::ToolRegistry;
use serde_json::{json, Value};

/// FR-003: tool registry — registering a tool makes it discoverable via
/// `has(name)`.
#[tokio::test]
async fn fr_003_register_and_lookup_tool() {
    let mut registry = ToolRegistry::new();
    registry
        .register(Box::new(CalculatorTool))
        .expect("register should succeed");

    assert!(registry.has("calculator"));
    assert_eq!(registry.list(), vec!["calculator"]);
}

/// FR-003: tool registry — `Tool::parameters` returns a JSON Schema with
/// the expected `required` fields.
#[test]
fn fr_003_tool_exposes_json_schema() {
    let tool = CalculatorTool;
    let schema = tool.parameters();
    let required = schema
        .get("required")
        .and_then(|v| v.as_array())
        .expect("schema must have a required array");
    assert!(required
        .iter()
        .any(|v| v == &Value::String("expression".into())));
}

/// FR-003: tool registry — `ToolRegistry::call` resolves a `ToolCall` to a
/// `ToolResponse` whose `id` matches the call's id.
#[tokio::test(flavor = "multi_thread")]
async fn fr_003_dispatch_tool_call_returns_response_with_id() {
    let mut registry = ToolRegistry::new();
    registry
        .register(Box::new(CalculatorTool))
        .expect("register should succeed");

    let call = ToolCall::new("calculator", json!({ "expression": "1+1" }), "call-1");
    let resp = registry.call(call).await.expect("call should succeed");
    assert_eq!(resp.id, "call-1");
    assert!(resp.error.is_none());
    assert!(resp.result.get("expression").is_some());
}

/// FR-003: tool registry — dispatching an unknown tool returns
/// `Error::Tool(...)` without panicking.
#[tokio::test]
async fn fr_003_unknown_tool_returns_error() {
    let registry = ToolRegistry::new();
    let call = ToolCall::new("nope", json!({}), "call-x");
    let err = registry
        .call(call)
        .await
        .expect_err("unknown tool should fail");
    let msg = err.to_string();
    assert!(msg.contains("Tool"), "got: {msg}");
    assert!(msg.contains("nope"), "got: {msg}");
}

/// FR-003: tool registry — duplicate registration of the same tool name
/// is rejected.
#[test]
fn fr_003_duplicate_tool_registration_fails() {
    let mut registry = ToolRegistry::new();
    registry
        .register(Box::new(CalculatorTool))
        .expect("first register should succeed");
    let err = registry
        .register(Box::new(CalculatorTool))
        .expect_err("duplicate register should fail");
    assert!(err.to_string().contains("calculator"));
}
