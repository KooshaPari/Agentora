//! In-memory [`StorePort`] for dispatch orchestration.

use std::sync::Mutex;

use async_trait::async_trait;
use substrate::domain::{StructuredResult, Task};
use substrate::{StorePort, SubstrateError};
use uuid::Uuid;

#[derive(Default)]
pub struct MemStore {
    tasks: Mutex<Vec<Task>>,
    results: Mutex<Vec<(Uuid, StructuredResult)>>,
}

#[async_trait]
impl StorePort for MemStore {
    async fn persist(&self, task: &Task) -> substrate::Result<()> {
        let mut tasks = self.tasks.lock().unwrap();
        tasks.retain(|t| t.id != task.id);
        tasks.push(task.clone());
        Ok(())
    }

    async fn load(&self, id: &Uuid) -> substrate::Result<Task> {
        self.tasks
            .lock()
            .unwrap()
            .iter()
            .find(|t| &t.id == id)
            .cloned()
            .ok_or_else(|| SubstrateError::NotFound(id.to_string()))
    }

    async fn persist_result(
        &self,
        task_id: &Uuid,
        result: &StructuredResult,
    ) -> substrate::Result<()> {
        self.results
            .lock()
            .unwrap()
            .push((*task_id, result.clone()));
        Ok(())
    }

    async fn claim_atomic(&self, id: &Uuid) -> substrate::Result<Task> {
        self.load(id).await
    }
}
