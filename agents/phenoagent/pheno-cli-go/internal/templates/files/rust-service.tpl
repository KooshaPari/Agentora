//! Application services

use async_trait::async_trait;
use crate::domain::{Entity, EntityRepository, DomainError};
use crate::application::dto::*;
use uuid::Uuid;

#[async_trait]
pub trait EntityService: Send + Sync {
    async fn create(&self, dto: CreateEntityDto) -> Result<Entity, DomainError>;
    async fn get_by_id(&self, id: Uuid) -> Result<Entity, DomainError>;
    async fn update(&self, id: Uuid, dto: UpdateEntityDto) -> Result<Entity, DomainError>;
    async fn delete(&self, id: Uuid) -> Result<(), DomainError>;
    async fn list(&self) -> Result<Vec<Entity>, DomainError>;
}

pub struct EntityServiceImpl<R: EntityRepository> {
    repository: R,
}

impl<R: EntityRepository> EntityServiceImpl<R> {
    pub fn new(repository: R) -> Self {
        Self { repository }
    }
}

#[async_trait]
impl<R: EntityRepository> EntityService for EntityServiceImpl<R> {
    async fn create(&self, dto: CreateEntityDto) -> Result<Entity, DomainError> {
        let entity = Entity::new(dto.name, dto.description);
        self.repository.create(&entity).await?;
        Ok(entity)
    }

    async fn get_by_id(&self, id: Uuid) -> Result<Entity, DomainError> {
        self.repository.find_by_id(id).await?
            .ok_or(DomainError::NotFound(id))
    }

    async fn update(&self, id: Uuid, dto: UpdateEntityDto) -> Result<Entity, DomainError> {
        let mut entity = self.get_by_id(id).await?;
        entity.update(dto.name, dto.description);
        self.repository.update(&entity).await?;
        Ok(entity)
    }

    async fn delete(&self, id: Uuid) -> Result<(), DomainError> {
        self.repository.delete(id).await
    }

    async fn list(&self) -> Result<Vec<Entity>, DomainError> {
        self.repository.list().await
    }
}
