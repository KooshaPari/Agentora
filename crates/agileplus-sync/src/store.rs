//! SyncMappingStore trait for persistence abstraction.
//!
//! Traceability: FR-SYNC-STORE / WP09-T056

use async_trait::async_trait;
use chrono::{DateTime, Utc};

use agileplus_domain::domain::sync_mapping::SyncMapping;

use crate::error::SyncError;

/// Persistence abstraction for sync mappings.
///
/// Implementations are expected to be cheaply cloneable (e.g., wrapping an
/// `Arc<dyn SyncMappingStore>`).
#[async_trait]
pub trait SyncMappingStore: Send + Sync {
    /// Persist a new sync mapping and return its assigned id.
    async fn create(&self, mapping: SyncMapping) -> Result<i64, SyncError>;

    /// Retrieve a mapping by entity type and local entity id.
    async fn get_by_entity(
        &self,
        entity_type: &str,
        entity_id: i64,
    ) -> Result<Option<SyncMapping>, SyncError>;

    /// Update the stored content hash and last-synced timestamp for a mapping.
    async fn update_hash(
        &self,
        id: i64,
        new_hash: String,
        synced_at: DateTime<Utc>,
    ) -> Result<(), SyncError>;

    /// Increment the conflict counter for a mapping.
    async fn increment_conflict(&self, id: i64) -> Result<(), SyncError>;

    /// Return all stored mappings.
    async fn list_all(&self) -> Result<Vec<SyncMapping>, SyncError>;
}

// ---------------------------------------------------------------------------
// In-memory implementation for tests
// ---------------------------------------------------------------------------

#[cfg(test)]
pub mod mem {
    use super::*;
    use std::sync::{Arc, Mutex};

    #[derive(Clone, Default)]
    pub struct InMemoryStore {
        inner: Arc<Mutex<Vec<SyncMapping>>>,
        next_id: Arc<Mutex<i64>>,
    }

    #[async_trait]
    impl SyncMappingStore for InMemoryStore {
        async fn create(&self, mut mapping: SyncMapping) -> Result<i64, SyncError> {
            let mut id_lock = self.next_id.lock().unwrap();
            *id_lock += 1;
            mapping.id = *id_lock;
            self.inner.lock().unwrap().push(mapping);
            Ok(*id_lock)
        }

        async fn get_by_entity(
            &self,
            entity_type: &str,
            entity_id: i64,
        ) -> Result<Option<SyncMapping>, SyncError> {
            let lock = self.inner.lock().unwrap();
            Ok(lock
                .iter()
                .find(|m| m.entity_type == entity_type && m.entity_id == entity_id)
                .cloned())
        }

        async fn update_hash(
            &self,
            id: i64,
            new_hash: String,
            synced_at: DateTime<Utc>,
        ) -> Result<(), SyncError> {
            let mut lock = self.inner.lock().unwrap();
            if let Some(m) = lock.iter_mut().find(|m| m.id == id) {
                m.content_hash = new_hash;
                m.last_synced_at = synced_at;
                Ok(())
            } else {
                Err(SyncError::Store(format!("mapping {id} not found")))
            }
        }

        async fn increment_conflict(&self, id: i64) -> Result<(), SyncError> {
            let mut lock = self.inner.lock().unwrap();
            if let Some(m) = lock.iter_mut().find(|m| m.id == id) {
                m.increment_conflict();
                Ok(())
            } else {
                Err(SyncError::Store(format!("mapping {id} not found")))
            }
        }

        async fn list_all(&self) -> Result<Vec<SyncMapping>, SyncError> {
            Ok(self.inner.lock().unwrap().clone())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::mem::InMemoryStore;
    use super::*;
    use agileplus_domain::domain::sync_mapping::SyncMapping;

    #[tokio::test]
    async fn create_and_retrieve() {
        let store = InMemoryStore::default();
        let m = SyncMapping::new("feature", 10, "plane-001", "hash-aaa");
        let id = store.create(m).await.unwrap();
        assert_eq!(id, 1);

        let found = store.get_by_entity("feature", 10).await.unwrap();
        assert!(found.is_some());
        assert_eq!(found.unwrap().plane_issue_id, "plane-001");
    }

    #[tokio::test]
    async fn update_hash() {
        let store = InMemoryStore::default();
        let m = SyncMapping::new("wp", 5, "plane-999", "old-hash");
        let id = store.create(m).await.unwrap();

        store
            .update_hash(id, "new-hash".to_string(), Utc::now())
            .await
            .unwrap();

        let found = store.get_by_entity("wp", 5).await.unwrap().unwrap();
        assert_eq!(found.content_hash, "new-hash");
    }

    #[tokio::test]
    async fn increment_conflict() {
        let store = InMemoryStore::default();
        let m = SyncMapping::new("feature", 7, "plane-777", "h");
        let id = store.create(m).await.unwrap();

        store.increment_conflict(id).await.unwrap();
        store.increment_conflict(id).await.unwrap();

        let found = store.get_by_entity("feature", 7).await.unwrap().unwrap();
        assert_eq!(found.conflict_count, 2);
    }

    #[tokio::test]
    async fn list_all() {
        let store = InMemoryStore::default();
        store
            .create(SyncMapping::new("a", 1, "p1", "h1"))
            .await
            .unwrap();
        store
            .create(SyncMapping::new("b", 2, "p2", "h2"))
            .await
            .unwrap();
        let all = store.list_all().await.unwrap();
        assert_eq!(all.len(), 2);
    }
}
