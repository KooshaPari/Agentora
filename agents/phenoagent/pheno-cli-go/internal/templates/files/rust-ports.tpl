//! Domain ports

use async_trait::async_trait;
use crate::domain::entities::Entity;
use uuid::Uuid;

#[async_trait]
pub trait EntityRepository: Send + Sync {
    async fn create(&self, entity: &Entity) -> Result<(), DomainError>;
    async fn find_by_id(&self, id: Uuid) -> Result<Option<Entity>, DomainError>;
    async fn update(&self, entity: &Entity) -> Result<(), DomainError>;
    async fn delete(&self, id: Uuid) -> Result<(), DomainError>;
    async fn list(&self) -> Result<Vec<Entity>, DomainError>;
}

#[derive(Debug, thiserror::Error)]
pub enum DomainError {
    #[error("Entity not found: {0}")]
    NotFound(Uuid),
    #[error("Invalid input: {0}")]
    InvalidInput(String),
    #[error("Repository error: {0}")]
    RepositoryError(String),
    #[error("Unknown error")]
    Unknown,
}
