//! Inbound (driving) ports — interfaces for driving adapters.

/// Marker trait for command inputs.
pub trait Command: Send + Sync {}

/// Marker trait for query inputs.
pub trait Query: Send + Sync {}

/// Marker trait for use case results.
pub trait UseCaseResult: Send + Sync {}
