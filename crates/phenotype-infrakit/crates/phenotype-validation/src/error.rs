//! Validation error types

use thiserror::Error;

pub type Result<T> = std::result::Result<T, ValidationError>;

#[derive(Error, Debug)]
pub enum ValidationError {
    #[error("validation failed: {0}")]
    ValidationFailed(String),

    #[error("schema error: {0}")]
    SchemaError(String),

    #[error("serialization error: {0}")]
    Serialization(String),

    #[error("invalid configuration: {0}")]
    ConfigError(String),

    #[error("{0}")]
    Other(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_error_display() {
        let err = ValidationError::ValidationFailed("test".to_string());
        assert_eq!(err.to_string(), "validation failed: test");
    }
}
