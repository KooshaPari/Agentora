use std::collections::HashMap;
use std::sync::RwLock;

use crate::error::{ForgecodeError, Result};
use crate::providers::ProviderRegistry;

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct AgentConfig {
    pub id: String,
    pub name: String,
    pub version: String,
    pub agent_type: String,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl AgentConfig {
    pub fn new(
        id: impl Into<String>,
        name: impl Into<String>,
        version: impl Into<String>,
        agent_type: impl Into<String>,
    ) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            version: version.into(),
            agent_type: agent_type.into(),
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(
        mut self,
        key: impl Into<String>,
        value: serde_json::Value,
    ) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

#[derive(Clone)]
pub struct Agent {
    config: AgentConfig,
}

impl Agent {
    pub fn new(config: AgentConfig) -> Self {
        Self { config }
    }

    pub fn config(&self) -> &AgentConfig {
        &self.config
    }

    pub async fn execute(
        &self,
        _input: &str,
        _registry: &ProviderRegistry,
    ) -> Result<String> {
        Ok(format!(
            "executed agent {} v{}",
            self.config.name, self.config.version
        ))
    }
}

pub struct AgentExecutor {
    agents: RwLock<HashMap<String, Agent>>,
}

impl Default for AgentExecutor {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentExecutor {
    pub fn new() -> Self {
        Self {
            agents: RwLock::new(HashMap::new()),
        }
    }

    pub fn register(&self, agent: Agent) -> Result<()> {
        let mut agents = self
            .agents
            .write()
            .map_err(|_| ForgecodeError::InvalidConfig("lock poisoned".into()))?;
        agents.insert(agent.config().id.clone(), agent);
        Ok(())
    }

    pub fn get(&self, id: &str) -> Option<Agent> {
        let agents = self.agents.read().ok()?;
        agents.get(id).cloned()
    }

    pub fn list_agents(&self) -> Vec<AgentConfig> {
        self.agents
            .read()
            .map(|a| a.values().map(|agent| agent.config().clone()).collect())
            .unwrap_or_default()
    }

    pub async fn execute(&self, agent_id: &str, input: &str, registry: &ProviderRegistry) -> Result<String> {
        let agent = self
            .get(agent_id)
            .ok_or_else(|| ForgecodeError::AgentNotFound(agent_id.into()))?;
        agent.execute(input, registry).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_config_creation() {
        let config = AgentConfig::new("agent-1", "Test Agent", "1.0.0", "chat");
        assert_eq!(config.id, "agent-1");
        assert_eq!(config.name, "Test Agent");
        assert_eq!(config.version, "1.0.0");
        assert_eq!(config.agent_type, "chat");
    }

    #[test]
    fn test_agent_config_with_metadata() {
        let config = AgentConfig::new("agent-1", "Test", "1.0.0", "chat")
            .with_metadata("key", serde_json::json!("value"));

        assert_eq!(config.metadata.get("key").unwrap(), "value");
    }

    #[test]
    fn test_agent_creation() {
        let config = AgentConfig::new("a1", "My Agent", "2.0.0", "code");
        let agent = Agent::new(config.clone());
        assert_eq!(agent.config().id, "a1");
    }

    #[tokio::test]
    async fn test_agent_execute() {
        let registry = ProviderRegistry::new();
        let config = AgentConfig::new("exec-test", "Execute Test", "1.0.0", "test");
        let agent = Agent::new(config);

        let result = agent.execute("test input", &registry).await.unwrap();
        assert!(result.contains("Execute Test"));
    }

    #[tokio::test]
    async fn test_executor_register_and_get() {
        let executor = AgentExecutor::new();
        let config = AgentConfig::new("e1", "Executor Test", "1.0.0", "test");
        let agent = Agent::new(config);

        executor.register(agent).unwrap();
        let retrieved = executor.get("e1");
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().config().name, "Executor Test");
    }

    #[tokio::test]
    async fn test_executor_list_agents() {
        let executor = AgentExecutor::new();
        executor
            .register(Agent::new(AgentConfig::new("a", "A", "1.0.0", "t")))
            .unwrap();
        executor
            .register(Agent::new(AgentConfig::new("b", "B", "1.0.0", "t")))
            .unwrap();

        let agents = executor.list_agents();
        assert_eq!(agents.len(), 2);
    }

    #[tokio::test]
    async fn test_executor_execute_not_found() {
        let executor = AgentExecutor::new();
        let registry = ProviderRegistry::new();

        let result = executor.execute("nonexistent", "input", &registry).await;
        assert!(matches!(result, Err(ForgecodeError::AgentNotFound(_))));
    }
}
