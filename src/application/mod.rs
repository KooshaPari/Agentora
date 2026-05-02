//! Application layer - Use cases

use async_trait::async_trait;
use crate::domain::{
    Agent, AgentConfig, Context, Output, Result,
    SkillRegistry, ToolRegistry,
    ShortTermMemory, MemoryEntry,
};
use std::sync::Arc;

/// Agent executor service
pub struct AgentExecutor {
    #[allow(dead_code)]
    config: AgentConfig,
    skills: Arc<SkillRegistry>,
    tools: Arc<ToolRegistry>,
    #[allow(dead_code)]
    memory: ShortTermMemory,
}

impl AgentExecutor {
    pub fn new(config: AgentConfig) -> Self {
        Self {
            config,
            skills: Arc::new(SkillRegistry::new()),
            tools: Arc::new(ToolRegistry::new()),
            memory: ShortTermMemory::default(),
        }
    }

    pub fn with_skills(mut self, skills: SkillRegistry) -> Self {
        self.skills = Arc::new(skills);
        self
    }

    pub fn with_tools(mut self, tools: ToolRegistry) -> Self {
        self.tools = Arc::new(tools);
        self
    }

    pub async fn run(&self, agent: &dyn Agent, input: String) -> Result<Output> {
        let mut ctx = Context::new(input);

        // Add system prompt to memory
        ctx.memory.push(MemoryEntry::system("You are a helpful assistant."));

        // Run agent
        agent.run(&ctx).await
    }

    pub fn get_tools(&self) -> Vec<&str> {
        self.tools.list()
    }

    pub fn get_skills(&self) -> Vec<&str> {
        self.skills.list()
    }
}

/// Simple agent implementation
pub struct SimpleAgent;

#[async_trait]
impl Agent for SimpleAgent {
    async fn run(&self, ctx: &Context) -> Result<Output> {
        Ok(Output::text(format!("Echo: {}", ctx.input)))
    }

    fn name(&self) -> &str {
        "simple"
    }
}
