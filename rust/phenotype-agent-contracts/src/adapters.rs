//! Built-in adapter implementations for phenotype ports.
//!
//! Provides in-memory implementations suitable for testing and prototyping.

use crate::error;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

/// In-memory repository implementation using HashMap.
///
/// Thread-safe and suitable for testing. Not recommended for production use.
pub struct InMemoryRepository<Id: Clone, Entity: Clone> {
    store: Arc<RwLock<HashMap<Id, Entity>>>,
}

impl<Id: Clone + Eq + std::hash::Hash, Entity: Clone> InMemoryRepository<Id, Entity> {
    /// Create a new in-memory repository.
    pub fn new() -> Self {
        Self {
            store: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a pre-populated repository.
    pub fn with_data(data: HashMap<Id, Entity>) -> Self {
        Self {
            store: Arc::new(RwLock::new(data)),
        }
    }

    /// Get the number of items in the repository.
    pub fn len(&self) -> usize {
        self.store
            .read()
            .expect("in-memory adapter lock poisoned")
            .len()
    }

    /// Check if the repository is empty.
    pub fn is_empty(&self) -> bool {
        self.store
            .read()
            .expect("in-memory adapter lock poisoned")
            .is_empty()
    }

    /// Clear all items from the repository.
    pub fn clear(&self) {
        self.store
            .write()
            .expect("in-memory adapter lock poisoned")
            .clear();
    }
}

impl<Id: Clone + Eq + std::hash::Hash + std::fmt::Debug, Entity: Clone> Default
    for InMemoryRepository<Id, Entity>
{
    fn default() -> Self {
        Self::new()
    }
}

impl<
        Id: Clone + Eq + std::hash::Hash + std::fmt::Debug + Send + Sync,
        Entity: Clone + Send + Sync,
    > crate::outbound::Repository for InMemoryRepository<Id, Entity>
{
    type Entity = Entity;
    type Id = Id;

    fn save(&self, id: Self::Id, entity: Self::Entity) -> error::Result<()> {
        self.store
            .write()
            .expect("in-memory adapter lock poisoned")
            .insert(id, entity);
        Ok(())
    }

    fn get(&self, id: &Self::Id) -> error::Result<Self::Entity> {
        self.store
            .read()
            .expect("in-memory adapter lock poisoned")
            .get(id)
            .cloned()
            .ok_or_else(|| error::ErrorKind::not_found(format!("Entity not found: {id:?}")))
    }

    fn delete(&self, id: &Self::Id) -> error::Result<()> {
        self.store
            .write()
            .expect("in-memory adapter lock poisoned")
            .remove(id);
        Ok(())
    }

    fn list(&self) -> error::Result<Vec<Self::Entity>> {
        Ok(self
            .store
            .read()
            .expect("in-memory adapter lock poisoned")
            .values()
            .cloned()
            .collect())
    }
}

/// In-memory cache implementation.
///
/// Thread-safe HashMap-backed cache.
pub struct InMemoryCache<Key: Clone, Value: Clone> {
    store: Arc<RwLock<HashMap<Key, Value>>>,
}

impl<Key: Clone + Eq + std::hash::Hash, Value: Clone> InMemoryCache<Key, Value> {
    /// Create a new in-memory cache.
    pub fn new() -> Self {
        Self {
            store: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Clear all entries from the cache.
    pub fn clear(&self) {
        self.store
            .write()
            .expect("in-memory adapter lock poisoned")
            .clear();
    }

    /// Get the number of cached entries.
    pub fn len(&self) -> usize {
        self.store
            .read()
            .expect("in-memory adapter lock poisoned")
            .len()
    }

    /// Check if the cache is empty.
    pub fn is_empty(&self) -> bool {
        self.store
            .read()
            .expect("in-memory adapter lock poisoned")
            .is_empty()
    }
}

impl<Key: Clone + Eq + std::hash::Hash, Value: Clone> Default for InMemoryCache<Key, Value> {
    fn default() -> Self {
        Self::new()
    }
}

impl<Key: Clone + Eq + std::hash::Hash + Send + Sync, Value: Clone + Send + Sync>
    crate::outbound::CachePort for InMemoryCache<Key, Value>
{
    type Key = Key;
    type Value = Value;

    fn get(&self, key: &Self::Key) -> error::Result<Option<Self::Value>> {
        Ok(self
            .store
            .read()
            .expect("in-memory adapter lock poisoned")
            .get(key)
            .cloned())
    }

    fn set(&self, key: Self::Key, value: Self::Value) -> error::Result<()> {
        self.store
            .write()
            .expect("in-memory adapter lock poisoned")
            .insert(key, value);
        Ok(())
    }

    fn invalidate(&self, key: &Self::Key) -> error::Result<()> {
        self.store
            .write()
            .expect("in-memory adapter lock poisoned")
            .remove(key);
        Ok(())
    }
}

/// In-memory event bus.
///
/// Collects events in memory. Suitable for testing.
pub struct InMemoryEventBus<Event: Clone> {
    events: Arc<RwLock<Vec<Event>>>,
}

impl<Event: Clone> InMemoryEventBus<Event> {
    /// Create a new in-memory event bus.
    pub fn new() -> Self {
        Self {
            events: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Get all published events.
    pub fn events(&self) -> Vec<Event> {
        self.events
            .read()
            .expect("in-memory adapter lock poisoned")
            .clone()
    }

    /// Get the number of events published.
    pub fn event_count(&self) -> usize {
        self.events
            .read()
            .expect("in-memory adapter lock poisoned")
            .len()
    }

    /// Clear all events.
    pub fn clear(&self) {
        self.events
            .write()
            .expect("in-memory adapter lock poisoned")
            .clear();
    }
}

impl<Event: Clone> Default for InMemoryEventBus<Event> {
    fn default() -> Self {
        Self::new()
    }
}

impl<Event: Clone + Send + Sync> crate::outbound::EventBus for InMemoryEventBus<Event> {
    type Event = Event;

    fn publish(&self, event: Self::Event) -> error::Result<()> {
        self.events
            .write()
            .expect("in-memory adapter lock poisoned")
            .push(event);
        Ok(())
    }

    fn publish_batch(&self, events: Vec<Self::Event>) -> error::Result<()> {
        self.events
            .write()
            .expect("in-memory adapter lock poisoned")
            .extend(events);
        Ok(())
    }
}

/// In-memory secret manager.
///
/// Stores secrets in plain HashMap. NOT FOR PRODUCTION.
pub struct InMemorySecretManager {
    secrets: Arc<RwLock<HashMap<String, String>>>,
}

impl InMemorySecretManager {
    /// Create a new in-memory secret manager.
    pub fn new() -> Self {
        Self {
            secrets: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Pre-load secrets.
    pub fn with_secrets(secrets: HashMap<String, String>) -> Self {
        Self {
            secrets: Arc::new(RwLock::new(secrets)),
        }
    }

    /// Clear all secrets.
    pub fn clear(&self) {
        self.secrets
            .write()
            .expect("in-memory adapter lock poisoned")
            .clear();
    }
}

impl Default for InMemorySecretManager {
    fn default() -> Self {
        Self::new()
    }
}

impl crate::outbound::SecretManager for InMemorySecretManager {
    fn get(&self, name: &str) -> error::Result<String> {
        self.secrets
            .read()
            .expect("in-memory adapter lock poisoned")
            .get(name)
            .cloned()
            .ok_or_else(|| error::ErrorKind::not_found(format!("Secret not found: {name}")))
    }

    fn set(&self, name: String, value: String) -> error::Result<()> {
        self.secrets
            .write()
            .expect("in-memory adapter lock poisoned")
            .insert(name, value);
        Ok(())
    }

    fn delete(&self, name: &str) -> error::Result<()> {
        self.secrets
            .write()
            .expect("in-memory adapter lock poisoned")
            .remove(name);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::outbound::{CachePort, EventBus, Repository, SecretManager};

    #[test]
    fn in_memory_repository_operations() {
        let repo: InMemoryRepository<String, String> = InMemoryRepository::new();
        repo.save("key1".to_string(), "value1".to_string()).unwrap();

        let value = repo.get(&"key1".to_string()).unwrap();
        assert_eq!(value, "value1");

        assert_eq!(repo.len(), 1);

        repo.delete(&"key1".to_string()).unwrap();
        assert!(repo.get(&"key1".to_string()).is_err());
    }

    #[test]
    fn in_memory_cache_operations() {
        let cache: InMemoryCache<String, String> = InMemoryCache::new();
        cache.set("key1".to_string(), "value1".to_string()).unwrap();

        let value = cache.get(&"key1".to_string()).unwrap();
        assert_eq!(value, Some("value1".to_string()));

        cache.invalidate(&"key1".to_string()).unwrap();
        let value = cache.get(&"key1".to_string()).unwrap();
        assert_eq!(value, None);
    }

    #[test]
    fn in_memory_event_bus() {
        let bus: InMemoryEventBus<String> = InMemoryEventBus::new();
        bus.publish("event1".to_string()).unwrap();
        bus.publish("event2".to_string()).unwrap();

        let events = bus.events();
        assert_eq!(events.len(), 2);
    }

    #[test]
    fn in_memory_secret_manager() {
        let manager = InMemorySecretManager::new();
        manager
            .set("api_key".to_string(), "secret123".to_string())
            .unwrap();

        let secret = manager.get("api_key").unwrap();
        assert_eq!(secret, "secret123");

        manager.delete("api_key").unwrap();
        assert!(manager.get("api_key").is_err());
    }
}
