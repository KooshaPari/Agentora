//! Static [`RoutingPort`] — routes all tasks to the agentkit engine.

use async_trait::async_trait;
use substrate::domain::{RoutingDecision, Task};
use substrate::RoutingPort;

pub struct AgentRoutingPort;

#[async_trait]
impl RoutingPort for AgentRoutingPort {
    async fn route_decision(&self, task: &Task) -> substrate::Result<RoutingDecision> {
        Ok(RoutingDecision {
            engine: "agentkit".into(),
            model: "default".into(),
            reason: Some(format!("default route for: {}", task.prompt)),
        })
    }
}
