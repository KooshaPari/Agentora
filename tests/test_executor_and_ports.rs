//! FR-005 acceptance tests: Application orchestration (`AgentExecutor`)
//! and adapter ports (LLM / MemoryPort / ToolExecutor).
//!
//! Each `#[test]` in this module is annotated with the FR it exercises.
//! FR-005: executor and ports

use agentkit::adapters::llm::EchoLLM;
use agentkit::adapters::memory::InMemoryAdapter;
use agentkit::application::{AgentExecutor, SimpleAgent};
use agentkit::domain::agents::AgentConfig;
use agentkit::domain::context::OutputContent;
use agentkit::domain::memory::{MemoryEntry, MemoryRole};
use agentkit::domain::ports::{LLM, MemoryPort};
use agentkit::domain::tools::CalculatorTool;
use agentkit::domain::tools::ToolRegistry;

/// FR-005: executor and ports — `AgentExecutor::run` builds a `Context`,
/// pre-seeds a system memory entry, and delegates to the agent.
#[tokio::test]
async fn fr_005_executor_runs_simple_agent_with_system_seed() {
    let executor = AgentExecutor::new(AgentConfig::new("executor-005"));
    let output = executor
        .run(&SimpleAgent, "hi".to_string())
        .await
        .expect("executor should run");
    match output.content {
        OutputContent::Text(s) => assert_eq!(s, "Echo: hi"),
        other => panic!("expected Text, got {other:?}"),
    }
}

/// FR-005: executor and ports — `AgentExecutor::with_skills` /
/// `with_tools` builder methods are honored and discoverable via
/// `get_skills` / `get_tools`.
#[test]
fn fr_005_executor_builder_exposes_skills_and_tools() {
    let mut tools = ToolRegistry::new();
    tools
        .register(Box::new(CalculatorTool))
        .expect("register calculator");
    let executor = AgentExecutor::new(AgentConfig::new("executor-builder"))
        .with_tools(tools);
    let names = executor.get_tools();
    assert!(names.contains(&"calculator"));
}

/// FR-005: executor and ports — `EchoLLM` adapter implements the `LLM`
/// port and is fully deterministic (no network).
#[tokio::test]
async fn fr_005_echo_llm_is_deterministic() {
    let llm = EchoLLM::new();
    let out = llm.complete("ping").await.expect("complete");
    assert_eq!(out, "ping");
    let out2 = llm.complete("ping").await.expect("complete");
    assert_eq!(out, out2, "EchoLLM must be deterministic");
}

/// FR-005: executor and ports — `InMemoryAdapter` implements the
/// `MemoryPort` port: add / recent / search work without network.
#[test]
fn fr_005_in_memory_adapter_implements_memory_port() {
    let adapter = InMemoryAdapter::new();
    adapter
        .add(MemoryEntry::user("alpha"))
        .expect("add alpha");
    adapter
        .add(MemoryEntry::assistant("beta"))
        .expect("add beta");

    let recent = adapter.recent(10).expect("recent");
    assert_eq!(recent.len(), 2);
    // Newest first.
    assert!(matches!(recent[0].role, MemoryRole::Assistant));
    assert!(matches!(recent[1].role, MemoryRole::User));

    let hits = adapter.search("beta").expect("search");
    assert_eq!(hits.len(), 1);
    assert!(hits[0].content.contains("beta"));
}

/// FR-005: executor and ports — `EchoLLM::with_prefix` is honored end-to-end
/// to confirm the adapter carries per-instance state.
#[tokio::test]
async fn fr_005_echo_llm_with_prefix() {
    let llm = EchoLLM::with_prefix("[echo] ");
    let out = llm.complete("ping").await.expect("complete");
    assert_eq!(out, "[echo] ping");
}
