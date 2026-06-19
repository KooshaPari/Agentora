//! Outbound ports (driven side) — interfaces for accessing external services.

use crate::error;
use std::collections::HashMap;

/// Repository port for persisting and retrieving domain entities.
pub trait Repository: Send + Sync {
    /// Entity type stored by this repository.
    type Entity: Send + Sync;
    /// Identifier type for entities.
    type Id: Clone + Send + Sync;

    /// Persist an entity.
    fn save(&self, id: Self::Id, entity: Self::Entity) -> error::Result<()>;
    /// Retrieve an entity by id.
    fn get(&self, id: &Self::Id) -> error::Result<Self::Entity>;
    /// Delete an entity by id.
    fn delete(&self, id: &Self::Id) -> error::Result<()>;
    /// List all entities.
    fn list(&self) -> error::Result<Vec<Self::Entity>>;
}

/// Cache port for storing and retrieving cached values.
pub trait CachePort: Send + Sync {
    /// Cache key type.
    type Key: Clone + Send + Sync;
    /// Cached value type.
    type Value: Clone + Send + Sync;

    /// Look up a cached value.
    fn get(&self, key: &Self::Key) -> error::Result<Option<Self::Value>>;
    /// Store a value in the cache.
    fn set(&self, key: Self::Key, value: Self::Value) -> error::Result<()>;
    /// Remove a cached entry.
    fn invalidate(&self, key: &Self::Key) -> error::Result<()>;
}

/// Event bus port for publishing domain events.
pub trait EventBus: Send + Sync {
    /// Event type published on this bus.
    type Event: Clone + Send + Sync;

    /// Publish a single event.
    fn publish(&self, event: Self::Event) -> error::Result<()>;
    /// Publish a batch of events.
    fn publish_batch(&self, events: Vec<Self::Event>) -> error::Result<()>;
}

/// Secret manager port for secure credential storage and retrieval.
pub trait SecretManager: Send + Sync {
    /// Retrieve a secret by name.
    fn get(&self, name: &str) -> error::Result<String>;
    /// Store a secret.
    fn set(&self, name: String, value: String) -> error::Result<()>;
    /// Delete a secret.
    fn delete(&self, name: &str) -> error::Result<()>;
}

/// Configuration loader port.
pub trait ConfigLoader: Send + Sync {
    /// Load configuration as key-value pairs.
    fn load(&self) -> error::Result<HashMap<String, String>>;
}
