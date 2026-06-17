//! In-memory repository

use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::RwLock;
use crate::domain::{Entity, EntityRepository, DomainError};
use uuid::Uuid;

pub struct InMemoryEntityRepository {
    entities: RwLock<HashMap<Uuid, Entity>>,
}

impl InMemoryEntityRepository {
    pub fn new() -> Self {
        Self {
            entities: RwLock::new(HashMap::new()),
        }
    }
}

impl Default for InMemoryEntityRepository {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl EntityRepository for InMemoryEntityRepository {
    async fn create(&self, entity: &Entity) -> Result<(), DomainError> {
        let mut entities = self.entities.write().unwrap();
        entities.insert(entity.id, entity.clone());
        Ok(())
    }

    async fn find_by_id(&self, id: Uuid) -> Result<Option<Entity>, DomainError> {
        let entities = self.entities.read().unwrap();
        Ok(entities.get(&id).cloned())
    }

    async fn update(&self, entity: &Entity) -> Result<(), DomainError> {
        let mut entities = self.entities.write().unwrap();
        entities.insert(entity.id, entity.clone());
        Ok(())
    }

    async fn delete(&self, id: Uuid) -> Result<(), DomainError> {
        let mut entities = self.entities.write().unwrap();
        entities.remove(&id);
        Ok(())
    }

    async fn list(&self) -> Result<Vec<Entity>, DomainError> {
        let entities = self.entities.read().unwrap();
        Ok(entities.values().cloned().collect())
    }
}
