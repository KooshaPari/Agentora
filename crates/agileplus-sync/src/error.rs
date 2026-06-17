//! Error types for agileplus-sync.
//!
//! Uses phenotype-error-core for canonical error types.

pub use phenotype_error_core::{DomainError, RepositoryError, StorageError};

use thiserror::Error;

/// Sync-specific error wrapper around canonical error types.
#[derive(Debug, Error)]
pub enum SyncError {
    #[error("store error: {0}")]
    Store(#[from] RepositoryError),

    #[error("NATS error: {0}")]
    Nats(String),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("conflict detected for entity {entity_type}/{entity_id}")]
    ConflictDetected { entity_type: String, entity_id: i64 },

    #[error("resolution failed: {0}")]
    ResolutionFailed(String),

    #[error("entity not found: {entity_type}/{entity_id}")]
    EntityNotFound { entity_type: String, entity_id: i64 },
}

impl From<async_nats::Error> for SyncError {
    fn from(e: async_nats::Error) -> Self {
        SyncError::Nats(e.to_string())
    }
}

impl From<StorageError> for SyncError {
    fn from(e: StorageError) -> Self {
        SyncError::Store(RepositoryError::Storage(e))
    }
}
