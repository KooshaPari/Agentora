//! FR-001 acceptance tests: Agent dispatch (Context -> Output).
//!
//! Each `#[test]` in this module is annotated with the FR it exercises.
//! FR-001: agent dispatch

use agentkit::domain::agents::{Agent, AgentConfig, AgentState, ExecutionStep};
use agentkit::domain::context::{Context, Output, OutputContent};
use agentkit::infrastructure::error::Result;
use async_trait::async_trait;

/// FR-001: agent dispatch — minimal `Agent` impl returns an `Output` for a
/// given `Context` and exposes `name` / `version`.
struct EchoAgent;

#[async_trait]
impl Agent for EchoAgent {
    async fn run(&self, ctx: &Context) -> Result<Output> {
        Ok(Output::text(format!("echo:{}", ctx.input)))
    }

    fn name(&self) -> &'static str {
        "echo"
    }
}

/// FR-001: agent dispatch — `Context::new` captures user input and assigns
/// a session id.
#[test]
fn fr_001_context_carries_user_input() {
    let ctx = Context::new("hello, agent");
    assert_eq!(ctx.input, "hello, agent");
    assert!(!ctx.session_id.is_empty());
    assert!(ctx.memory.is_empty());
    assert!(ctx.tool_calls.is_empty());
    assert!(ctx.tool_results.is_empty());
}

/// FR-001: agent dispatch — running an agent returns a typed `Output`
/// that can be matched on as `OutputContent::Text`.
#[tokio::test]
async fn fr_001_agent_run_returns_text_output() {
    let agent = EchoAgent;
    let ctx = Context::new("ping");
    let output = agent.run(&ctx).await.expect("agent run should succeed");
    match output.content {
        OutputContent::Text(s) => assert_eq!(s, "echo:ping"),
        other => panic!("expected Text, got {other:?}"),
    }
    assert_eq!(agent.name(), "echo");
}

/// FR-001: agent dispatch — `AgentConfig` builder is honored end-to-end.
#[test]
fn fr_001_agent_config_builder_applied() {
    let cfg = AgentConfig::new("fr-001")
        .model("gpt-4o-mini")
        .temperature(0.25);
    assert_eq!(cfg.name, "fr-001");
    assert_eq!(cfg.model, "gpt-4o-mini");
    assert!((cfg.temperature - 0.25).abs() < f32::EPSILON);
}

/// FR-001: agent dispatch — `ExecutionStep` and `AgentState` model the
/// observable lifecycle of an agent.
#[test]
fn fr_001_execution_step_and_state_default() {
    let mut step = ExecutionStep::new(1);
    assert_eq!(step.step_number, 1);
    // Default state is `Thinking`.
    assert!(matches!(step.state, AgentState::Thinking));
    step.state = AgentState::Done;
    assert!(matches!(step.state, AgentState::Done));
}
