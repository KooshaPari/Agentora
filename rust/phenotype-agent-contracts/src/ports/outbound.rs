//! Outbound (driven) port markers — category traits for driven adapters.

/// Marker trait for repository ports.
pub trait RepositoryPort: Send + Sync {}

/// Marker trait for cache ports.
pub trait CachePort: Send + Sync {}

/// Marker trait for secret ports.
pub trait SecretPort: Send + Sync {}
