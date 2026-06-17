//! Query handlers - Read operations
//!
//! Queries represent read operations in the application.
//! Following CQRS pattern.

use crate::domain::{Context, Output, Result};
use async_trait::async_trait;

/// Query handler trait
#[async_trait]
pub trait QueryHandler: Send + Sync {
    /// Handle a query
    async fn handle(&self, ctx: &Context) -> Result<Output>;
}

/// Default query handler
pub struct DefaultQueryHandler<F, Fut>
where
    F: Fn(&Context) -> Fut,
    Fut: std::future::Future<Output = Result<Output>>,
{
    handler: F,
}

impl<F, Fut> DefaultQueryHandler<F, Fut>
where
    F: Fn(&Context) -> Fut + Send + Sync,
    Fut: std::future::Future<Output = Result<Output>> + Send,
{
    pub fn new(handler: F) -> Self {
        Self { handler }
    }
}

#[async_trait]
impl<F, Fut> QueryHandler for DefaultQueryHandler<F, Fut>
where
    F: Fn(&Context) -> Fut + Send + Sync + 'static,
    Fut: std::future::Future<Output = Result<Output>> + Send,
{
    async fn handle(&self, ctx: &Context) -> Result<Output> {
        (self.handler)(ctx).await
    }
}

/// Query executor
pub struct QueryExecutor {
    handlers: Vec<(String, Box<dyn QueryHandler>)>,
}

impl QueryExecutor {
    pub fn new() -> Self {
        Self {
            handlers: Vec::new(),
        }
    }

    pub fn register(mut self, name: &str, handler: Box<dyn QueryHandler>) -> Self {
        self.handlers.push((name.to_string(), handler));
        self
    }

    pub async fn execute(&self, name: &str, ctx: &Context) -> Result<Output> {
        let handler = self
            .handlers
            .iter()
            .find(|(n, _)| n == name)
            .map(|(_, h)| h)
            .ok_or_else(|| crate::domain::DomainError::CommandNotFound(name.to_string()))?;

        handler.handle(ctx).await
    }
}

impl Default for QueryExecutor {
    fn default() -> Self {
        Self::new()
    }
}
