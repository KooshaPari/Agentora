//! FR-002 acceptance tests: Skill registry with unique names and JSON
//! parameters.
//!
//! Each `#[test]` in this module is annotated with the FR it exercises.
//! FR-002: skill registry

use agentkit::domain::skills::{Skill, SkillRegistry, WebSearchSkill};
use serde_json::{json, Value};

/// FR-002: skill registry — registering a skill makes it discoverable via
/// `has(name)` and `list()`.
#[tokio::test]
async fn fr_002_register_and_list_skills() {
    let mut registry = SkillRegistry::new();
    registry
        .register(Box::new(WebSearchSkill))
        .expect("register should succeed");

    assert!(registry.has("web_search"));
    let names = registry.list();
    assert_eq!(names, vec!["web_search"]);
}

/// FR-002: skill registry — registering a duplicate name fails with
/// `Error::Skill(...)`.
#[test]
fn fr_002_duplicate_skill_registration_fails() {
    let mut registry = SkillRegistry::new();
    registry
        .register(Box::new(WebSearchSkill))
        .expect("first register should succeed");

    let err = registry
        .register(Box::new(WebSearchSkill))
        .expect_err("duplicate register should fail");
    let msg = err.to_string();
    assert!(msg.contains("Skill"), "got: {msg}");
    assert!(msg.contains("web_search"), "got: {msg}");
}

/// FR-002: skill registry — `Skill::execute` accepts a `serde_json::Value`
/// parameter object and returns a `SkillResult` with `success=true`.
#[tokio::test]
async fn fr_002_skill_execute_accepts_json_params() {
    let skill = WebSearchSkill;
    let out: agentkit::infrastructure::error::Result<_> = skill
        .execute(json!({ "query": "rust agents" }))
        .await
        .into();
    let result = out.expect("skill execute should succeed");
    assert!(result.success);
    assert_eq!(result.data.get("query"), Some(&Value::String("rust agents".into())));
}

/// FR-002: skill registry — `Skill::description` provides a human-readable
/// string for tools that surface it.
#[test]
fn fr_002_skill_description_is_non_empty() {
    let skill = WebSearchSkill;
    let desc = skill.description();
    assert!(!desc.is_empty());
    assert!(desc.to_lowercase().contains("search"));
}

/// FR-002: skill registry — looking up an unknown skill via `get` returns
/// `None` (registry stays consistent under missing names).
#[test]
fn fr_002_get_unknown_skill_returns_none() {
    let registry = SkillRegistry::new();
    assert!(registry.get("does-not-exist").is_none());
    assert!(!registry.has("does-not-exist"));
}
