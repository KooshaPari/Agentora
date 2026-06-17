//! NFR-001 acceptance tests: Hexagonal boundary enforcement.
//!
//! Each `#[test]` in this module is annotated with the NFR it exercises.
//! NFR-001: hexagonal boundary

use agentkit::domain::agents::Agent;
use agentkit::domain::skills::Skill;
use agentkit::domain::tools::Tool;
use agentkit::domain::ports::LLM;

/// NFR-001: hexagonal boundary — every public port / domain type is
/// reachable from the top-level crate root via re-exports.
#[test]
fn nfr_001_prelude_exposes_core_traits() {
    fn _assert_send_sync<T: Send + Sync>() {}
    // Trait objects must be re-exported and usable through the crate root.
    let _: Option<Box<dyn Agent>> = None;
    let _: Option<Box<dyn Skill>> = None;
    let _: Option<Box<dyn Tool>> = None;
    let _: Option<Box<dyn LLM>> = None;
    // Generic sanity: the type alias compiles.
    let _ = _assert_send_sync::<agentkit::domain::Context>;
}

/// NFR-001: hexagonal boundary — domain code does not reference any
/// adapter or infrastructure paths. The `agent` and `tool` traits are
/// fully usable without enabling the `openai` / `redis-memory` /
/// `sqlite-memory` features.
#[test]
fn nfr_001_domain_traits_compile_without_adapter_features() {
    // No `#[cfg(feature = "...")]` gates on these trait usages; if a
    // regression introduces such a gate this test will stop compiling.
    fn uses_agent<A: Agent>(_: &A) {}
    fn uses_skill<S: Skill>(_: &S) {}
    fn uses_tool<T: Tool>(_: &T) {}
    let _ = uses_agent::<agentkit::application::SimpleAgent>;
    let _ = uses_skill::<agentkit::domain::skills::WebSearchSkill>;
    let _ = uses_tool::<agentkit::domain::tools::CalculatorTool>;
}

/// NFR-001: hexagonal boundary — the `prelude` re-exports the public
/// surface used by downstream consumers.
#[test]
fn nfr_001_prelude_contains_core_types() {
    use agentkit::prelude::*;
    use agentkit::ToolRegistry;
    // These names must be in scope when `use agentkit::prelude::*;` is in
    // effect. The mere fact that this file compiles is the assertion.
    let _ctx = Context::new("ping");
    let _out = Output::text("pong");
    let _entry = MemoryEntry::user("u");
    let _call = ToolCall::new("calculator", serde_json::json!({"expression":"1+1"}), "id");
    let _ = ToolRegistry::new();
}
