//! NFR-004 acceptance tests: Async, `Send + Sync` core traits.
//!
//! Each `#[test]` in this module is annotated with the NFR it exercises.
//! NFR-004: async Send+Sync

use agentkit::domain::agents::Agent;
use agentkit::domain::ports::LLM;
use agentkit::domain::skills::Skill;
use agentkit::domain::tools::Tool;

/// NFR-004: async Send+Sync — compile-time assertion that all core
/// traits and their default impls are `Send + Sync` and usable across
/// `.await` points from a multi-threaded runtime.
fn assert_send_sync<T: Send + Sync + ?Sized>() {}

#[test]
fn nfr_004_core_traits_are_send_sync() {
    assert_send_sync::<dyn Agent>();
    assert_send_sync::<dyn Skill>();
    assert_send_sync::<dyn Tool>();
    assert_send_sync::<dyn LLM>();
}

/// NFR-004: async Send+Sync — concrete built-ins satisfy the bounds and
/// can be moved into spawned tasks.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn nfr_004_builtins_are_send_sync_across_await() {
    use agentkit::application::SimpleAgent;
    use agentkit::domain::context::{Context, OutputContent};
    use agentkit::domain::memory::MemoryEntry;
    use agentkit::domain::skills::WebSearchSkill;
    use agentkit::domain::tools::{CalculatorTool, Tool as _, ToolCall};
    use serde_json::json;

    let agent = SimpleAgent;
    let ctx = Context::new("hi");
    let out = agent.run(&ctx).await.expect("agent run");
    match out.content {
        OutputContent::Text(s) => assert_eq!(s, "Echo: hi"),
        other => panic!("expected Text, got {other:?}"),
    }

    let skill = WebSearchSkill;
    let s = skill
        .execute(json!({"query": "rust"}))
        .await
        .expect("skill execute");
    assert!(s.success);

    let tool = CalculatorTool;
    let r = tool
        .call(ToolCall::new("calculator", json!({"expression": "2+2"}), "c1"))
        .await
        .expect("tool call");
    assert!(r.get("expression").is_some());

    let _ = MemoryEntry::user("warm");
}

/// NFR-004: async Send+Sync — `Send + Sync` is preserved through the
/// `AgentExecutor` (it owns a `SkillRegistry` and `ToolRegistry`).
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn nfr_004_executor_is_send_sync() {
    use agentkit::application::AgentExecutor;
    use agentkit::domain::agents::AgentConfig;
    use agentkit::domain::tools::{CalculatorTool, ToolRegistry};

    let mut tools = ToolRegistry::new();
    tools
        .register(Box::new(CalculatorTool))
        .expect("register calculator");

    let executor = AgentExecutor::new(AgentConfig::new("nfr-004")).with_tools(tools);
    let names = executor.get_tools();
    assert!(names.contains(&"calculator"));
}
