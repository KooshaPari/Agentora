//! In-memory / stub adapters for #79 ports (tests + dry-run).
//!
//! Production backends (Langfuse, harness_queue) wire outside this crate.

use async_trait::async_trait;
use serde_json::Value;

use crate::agent::AgentError;
use crate::sdk_dto::{CellRecord, EvalHookRef, RunHandle, RunStatus};
use crate::sdk_ports::{EvalGardenPort, ObservabilityPort, SchedulerQueuePort};

/// In-memory scheduler for tests / dry-run (fail loud on unknown ids).
#[derive(Default)]
pub struct InMemoryScheduler {
    // Intentionally empty — enqueue always returns queued handle; poll/cancel need map.
    // Use std::sync::Mutex for simplicity in contracts crate.
    state: std::sync::Mutex<std::collections::HashMap<String, RunStatus>>,
}

impl InMemoryScheduler {
    /// Create empty scheduler.
    pub fn new() -> Self {
        Self::default()
    }
}

#[async_trait]
impl SchedulerQueuePort for InMemoryScheduler {
    async fn enqueue(&self, _payload: Value) -> Result<RunHandle, AgentError> {
        let run_id = uuid::Uuid::new_v4().to_string();
        self.state
            .lock()
            .map_err(|e| AgentError::Config(format!("scheduler lock: {e}")))?
            .insert(run_id.clone(), RunStatus::Queued);
        Ok(RunHandle {
            run_id,
            status: RunStatus::Queued,
        })
    }

    async fn poll(&self, run_id: &str) -> Result<RunHandle, AgentError> {
        let guard = self
            .state
            .lock()
            .map_err(|e| AgentError::Config(format!("scheduler lock: {e}")))?;
        let status = guard
            .get(run_id)
            .cloned()
            .ok_or_else(|| AgentError::Config(format!("unknown run_id: {run_id}")))?;
        Ok(RunHandle {
            run_id: run_id.to_string(),
            status,
        })
    }

    async fn cancel(&self, run_id: &str) -> Result<(), AgentError> {
        let mut guard = self
            .state
            .lock()
            .map_err(|e| AgentError::Config(format!("scheduler lock: {e}")))?;
        let slot = guard
            .get_mut(run_id)
            .ok_or_else(|| AgentError::Config(format!("unknown run_id: {run_id}")))?;
        *slot = RunStatus::Cancelled;
        Ok(())
    }
}

/// No-op observability that **fails loud** on flush if never configured.
#[derive(Debug, Default)]
pub struct UnconfiguredObservability;

#[async_trait]
impl ObservabilityPort for UnconfiguredObservability {
    async fn start_span(&self, _name: &str, _attributes: Value) -> Result<String, AgentError> {
        Err(AgentError::Config(
            "ObservabilityPort unconfigured; wire Langfuse/cockpit backend".into(),
        ))
    }

    async fn score(
        &self,
        _span_id: &str,
        _name: &str,
        _value: f64,
        _comment: Option<String>,
    ) -> Result<(), AgentError> {
        Err(AgentError::Config(
            "ObservabilityPort unconfigured; wire Langfuse/cockpit backend".into(),
        ))
    }

    async fn flush(&self) -> Result<(), AgentError> {
        Err(AgentError::Config(
            "ObservabilityPort unconfigured; wire Langfuse/cockpit backend".into(),
        ))
    }
}

/// Recording Garden port for tests (in-memory).
#[derive(Default)]
pub struct RecordingEvalGarden {
    hooks: std::sync::Mutex<Vec<EvalHookRef>>,
    cells: std::sync::Mutex<Vec<CellRecord>>,
    evidence: std::sync::Mutex<Vec<Value>>,
}

impl RecordingEvalGarden {
    /// Create empty recorder.
    pub fn new() -> Self {
        Self::default()
    }

    /// Snapshot attached hooks.
    pub fn hooks(&self) -> Result<Vec<EvalHookRef>, AgentError> {
        Ok(self
            .hooks
            .lock()
            .map_err(|e| AgentError::Config(format!("garden lock: {e}")))?
            .clone())
    }
}

#[async_trait]
impl EvalGardenPort for RecordingEvalGarden {
    async fn attach(&self, hook: EvalHookRef) -> Result<(), AgentError> {
        self.hooks
            .lock()
            .map_err(|e| AgentError::Config(format!("garden lock: {e}")))?
            .push(hook);
        Ok(())
    }

    async fn record_cell(&self, cell: CellRecord) -> Result<(), AgentError> {
        self.cells
            .lock()
            .map_err(|e| AgentError::Config(format!("garden lock: {e}")))?
            .push(cell);
        Ok(())
    }

    async fn gate_evidence(&self, evidence: Value) -> Result<(), AgentError> {
        self.evidence
            .lock()
            .map_err(|e| AgentError::Config(format!("garden lock: {e}")))?
            .push(evidence);
        Ok(())
    }
}
