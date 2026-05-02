//! Agent domain - Core agent entities

use async_trait::async_trait;
use crate::domain::{Context, Result, Output};

/// Agent trait - implement this to create an agent
#[async_trait]
pub trait Agent: Send + Sync {
    /// Run the agent
    async fn run(&self, ctx: &Context) -> Result<Output>;

    /// Get agent name
    fn name(&self) -> &str { "agent" }

    /// Get agent version
    fn version(&self) -> &str { "1.0.0" }
}

/// Agent configuration
#[derive(Debug, Clone)]
pub struct AgentConfig {
    pub name: String,
    pub model: String,
    pub temperature: f32,
    pub max_tokens: u32,
    pub tools_enabled: bool,
    pub memory_enabled: bool,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            name: "agent".to_string(),
            model: "gpt-4".to_string(),
            temperature: 0.7,
            max_tokens: 4096,
            tools_enabled: true,
            memory_enabled: true,
        }
    }
}

impl AgentConfig {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            ..Default::default()
        }
    }

    pub fn model(mut self, model: impl Into<String>) -> Self {
        self.model = model.into();
        self
    }

    pub fn temperature(mut self, temp: f32) -> Self {
        self.temperature = temp;
        self
    }
}

/// Agent state
#[derive(Debug, Clone, Default)]
pub enum AgentState {
    #[default]
    Idle,
    Thinking,
    Acting,
    WaitingForTool,
    Done,
    Error(String),
}

/// Execution step for tracing
#[derive(Debug, Clone)]
pub struct ExecutionStep {
    pub step_number: u32,
    pub state: AgentState,
    pub thought: Option<String>,
    pub action: Option<String>,
    pub observation: Option<String>,
}

impl ExecutionStep {
    pub fn new(step_number: u32) -> Self {
        Self {
            step_number,
            state: AgentState::Thinking,
            thought: None,
            action: None,
            observation: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_config() {
        let config = AgentConfig::new("test")
            .model("gpt-3.5")
            .temperature(0.5);

        assert_eq!(config.name, "test");
        assert_eq!(config.model, "gpt-3.5");
        assert_eq!(config.temperature, 0.5);
    }
}
