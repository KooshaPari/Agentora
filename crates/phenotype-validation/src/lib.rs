//! Validation Utilities
//!
//! Provides data validation for Phenotype types.

pub mod email;
pub mod schema;
pub mod types;

pub use email::{validate_email, EmailValidationError};
pub use schema::{Schema, SchemaValidationError};

/// Validation result type
pub type ValidationResult<T> = Result<T, ValidationError>;

/// General validation error
#[derive(Debug, thiserror::Error)]
pub enum ValidationError {
    #[error("Email validation failed: {0}")]
    Email(#[from] EmailValidationError),
    #[error("Schema validation failed: {0}")]
    Schema(#[from] SchemaValidationError),
    #[error("Custom validation failed: {0}")]
    Custom(String),
}
