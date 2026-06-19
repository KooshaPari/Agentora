//! Contract error types for agent and adapter ports.

use thiserror::Error;

/// Domain-level contract error.
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum DomainError {
    /// Entity not found.
    #[error("entity not found: {entity} {id}")]
    NotFound {
        /// Entity type name.
        entity: String,
        /// Entity identifier.
        id: String,
    },

    /// Validation failure.
    #[error("validation failed: {0}")]
    Validation(String),

    /// Operation not permitted.
    #[error("operation not permitted: {0}")]
    NotPermitted(String),

    /// Other contract error.
    #[error("{0}")]
    Other(String),
}

/// Result type for contract operations.
pub type Result<T> = std::result::Result<T, DomainError>;

/// Convenience helpers for constructing contract errors.
pub struct ErrorKind;

impl ErrorKind {
    /// Create a not-found error with a descriptive message.
    pub fn not_found(msg: String) -> DomainError {
        DomainError::NotFound {
            entity: "entity".to_string(),
            id: msg,
        }
    }
}
