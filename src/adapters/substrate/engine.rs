//! [`EnginePort`] adapter that runs an agentkit [`Agent`].

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use substrate::domain::{
    ConversationDump, EngineCapabilities, Mailbox, Session, StructuredResult, Task, TaskState,
};
use substrate::EnginePort;

use crate::domain::{Agent, Context, MemoryEntry, OutputContent};

pub struct AgentEngine {
    agent: Mutex<Option<Arc<dyn Agent>>>,
    outputs: Mutex<HashMap<String, String>>,
}

impl Default for AgentEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentEngine {
    pub fn new() -> Self {
        Self {
            agent: Mutex::new(None),
            outputs: Mutex::new(HashMap::new()),
        }
    }

    pub fn set_agent(&self, agent: Arc<dyn Agent>) {
        *self.agent.lock().unwrap() = Some(agent);
    }

    async fn run_prompt(&self, prompt: &str) -> substrate::Result<String> {
        let agent = self
            .agent
            .lock()
            .unwrap()
            .clone()
            .ok_or_else(|| substrate::SubstrateError::Engine("no agent configured".into()))?;

        let mut ctx = Context::new(prompt);
        ctx.memory
            .push(MemoryEntry::system("You are a helpful assistant."));

        let output = agent
            .run(&ctx)
            .await
            .map_err(|e| substrate::SubstrateError::Engine(e.to_string()))?;

        match output.content {
            OutputContent::Text(text) => Ok(text),
            OutputContent::Json(value) => Ok(value.to_string()),
            OutputContent::Error(message) => {
                Err(substrate::SubstrateError::Engine(message))
            }
        }
    }
}

#[async_trait]
impl EnginePort for AgentEngine {
    async fn start(&self, task: &Task) -> substrate::Result<Session> {
        let text = self.run_prompt(&task.prompt).await?;
        let conv_id = format!("conv-{}", task.id);
        self.outputs.lock().unwrap().insert(conv_id.clone(), text);
        Ok(Session {
            conv_id,
            pid: None,
            logfile: None,
        })
    }

    async fn resume(&self, conv_id: &str, prompt: &str) -> substrate::Result<Session> {
        let text = self.run_prompt(prompt).await?;
        self.outputs.lock().unwrap().insert(conv_id.to_string(), text);
        Ok(Session {
            conv_id: conv_id.into(),
            pid: None,
            logfile: None,
        })
    }

    async fn dump(&self, conv_id: &str) -> substrate::Result<ConversationDump> {
        let raw = self
            .outputs
            .lock()
            .unwrap()
            .get(conv_id)
            .cloned()
            .unwrap_or_default();
        Ok(ConversationDump {
            conversation_id: conv_id.to_string(),
            raw,
        })
    }

    async fn cancel(&self, _conv_id: &str) -> substrate::Result<()> {
        Ok(())
    }

    async fn wire_mailbox(&self, _conv_id: &str, _mailbox: &Mailbox) -> substrate::Result<()> {
        Ok(())
    }

    fn extract_result(&self, dump: &ConversationDump) -> substrate::Result<StructuredResult> {
        Ok(StructuredResult {
            text: dump.raw.clone(),
            artifacts: vec![],
            pr_urls: vec![],
            status: TaskState::Completed,
        })
    }

    fn capabilities(&self) -> EngineCapabilities {
        EngineCapabilities {
            supports_resume: true,
            supports_subagents: false,
            supports_mcp_import: false,
        }
    }
}
