//! Validator ports (interfaces)

use crate::types::{ValidationContext, ValidationResult};
use async_trait::async_trait;

pub type Result<T> = std::result::Result<T, crate::error::ValidationError>;

#[async_trait]
pub trait ValidatorPort: Send + Sync {
    async fn validate(&self, context: &ValidationContext) -> Result<ValidationResult>;
}

pub trait CustomValidator: Send + Sync {
    fn validate(
        &self,
        value: &serde_json::Value,
        params: &std::collections::HashMap<String, serde_json::Value>,
    ) -> bool;
}
