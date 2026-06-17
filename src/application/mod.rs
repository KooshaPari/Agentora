//! Application layer - Use cases (substrate dispatch orchestration)

use crate::adapters::substrate::{AgentEngine, AgentRoutingPort, MemStore, NoopTransport};
use crate::adapters::substrate::{SkillRegistry, ToolRegistry};
use crate::domain::{Agent, AgentConfig, Context, Output, Result, ShortTermMemory};
use async_trait::async_trait;
use std::env;
use std::sync::Arc;
use substrate::domain::Task;
use substrate::ports::DispatchApi;
use substrate::{
    DispatchPlanner, DispatchService, EngineCandidate, EngineCapabilities, PlanRequest,
    RoutingPort, SessionMode,
};

/// Agent executor service — orchestrates runs via substrate [`DispatchService`].
pub struct AgentExecutor {
    #[allow(dead_code)]
    config: AgentConfig,
    engine: Arc<AgentEngine>,
    dispatch: DispatchService<AgentEngine, MemStore, NoopTransport>,
    skills: Arc<SkillRegistry>,
    tools: Arc<ToolRegistry>,
    #[allow(dead_code)]
    memory: ShortTermMemory,
}

impl AgentExecutor {
    pub fn new(config: AgentConfig) -> Self {
        let engine = Arc::new(AgentEngine::new());
        let store = Arc::new(MemStore::default());
        let dispatch = DispatchService::new(engine.clone(), store, Arc::new(NoopTransport));
        Self {
            config,
            engine,
            dispatch,
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

    pub async fn run<A>(&self, agent: A, input: String) -> Result<Output>
    where
        A: Agent + Send + Sync + 'static,
    {
        self.engine.set_agent(Arc::new(agent));

        let cwd = env::current_dir()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|_| ".".into());

        let task = Task::new(&input, &cwd);
        let route = AgentRoutingPort
            .route_decision(&task)
            .await
            .map_err(|e| crate::domain::Error::Execution(e.to_string()))?;

        let engines = vec![EngineCandidate {
            name: "agentkit".into(),
            capabilities: EngineCapabilities {
                supports_resume: true,
                supports_subagents: false,
                supports_mcp_import: false,
            },
        }];

        let spec = substrate::TaskSpec::new(&input, &cwd);
        let _plan = DispatchPlanner::plan(&PlanRequest {
            spec: &spec,
            engines: &engines,
            explicit_engine: Some("agentkit"),
            session_mode: Some(SessionMode::InProcess),
            routing_engine: Some(&route.engine),
        })
        .map_err(|e| crate::domain::Error::Execution(e.to_string()))?;

        let result = self
            .dispatch
            .dispatch(task)
            .await
            .map_err(|e| crate::domain::Error::Execution(e.to_string()))?;

        Ok(Output::text(result.text))
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
