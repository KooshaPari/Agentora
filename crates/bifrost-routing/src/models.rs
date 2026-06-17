use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingRequest {
    pub model: String,
    pub prompt: String,
    pub task_type: Option<String>,
}

impl RoutingRequest {
    pub fn new(model: impl Into<String>, prompt: impl Into<String>) -> Self {
        Self {
            model: model.into(),
            prompt: prompt.into(),
            task_type: None,
        }
    }

    pub fn with_task(mut self, task: impl Into<String>) -> Self {
        self.task_type = Some(task.into());
        self
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterDecision {
    pub provider: String,
    pub reasoning: String,
    pub estimated_cost_usd: f64,
    pub estimated_latency_ms: u32,
    pub confidence: f64,
}

impl RouterDecision {
    pub fn new(provider: impl Into<String>) -> Self {
        Self {
            provider: provider.into(),
            reasoning: String::new(),
            estimated_cost_usd: 0.0,
            estimated_latency_ms: 0,
            confidence: 0.0,
        }
    }

    pub fn with_reasoning(mut self, reasoning: impl Into<String>) -> Self {
        self.reasoning = reasoning.into();
        self
    }

    pub fn with_cost(mut self, cost: f64) -> Self {
        self.estimated_cost_usd = cost;
        self
    }

    pub fn with_latency(mut self, latency: u32) -> Self {
        self.estimated_latency_ms = latency;
        self
    }

    pub fn with_confidence(mut self, confidence: f64) -> Self {
        self.confidence = confidence;
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_routing_request_builder() {
        let request = RoutingRequest::new("gpt-4o", "Hello world").with_task("chat");
        assert_eq!(request.model, "gpt-4o");
        assert_eq!(request.prompt, "Hello world");
        assert_eq!(request.task_type, Some("chat".to_string()));
    }

    #[test]
    fn test_router_decision_builder() {
        let decision = RouterDecision::new("gpt-4o")
            .with_reasoning("Selected for analysis")
            .with_cost(0.003)
            .with_latency(500)
            .with_confidence(0.95);
        assert_eq!(decision.provider, "gpt-4o");
        assert_eq!(decision.estimated_cost_usd, 0.003);
    }
}
