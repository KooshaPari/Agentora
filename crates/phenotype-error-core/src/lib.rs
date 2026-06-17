//! Error core types for Phenotype

use thiserror::Error;

/// Core error type for Phenotype
#[derive(Error, Debug, Clone)]
pub enum PhenotypeError {
    /// Configuration error
    #[error("Configuration error: {0}")]
    Config(String),
    /// IO error
    #[error("IO error: {0}")]
    Io(String),
    /// Validation error
    #[error("Validation error: {0}")]
    Validation(String),
    /// Unknown error
    #[error("Unknown error: {0}")]
    Unknown(String),
}

/// API error type
#[derive(Error, Debug, Clone)]
#[error("API error: {0}")]
pub struct ApiError(pub String);

/// Config error type
#[derive(Error, Debug, Clone)]
#[error("Config error: {0}")]
pub struct ConfigError(pub String);

/// Domain error type
#[derive(Error, Debug, Clone)]
#[error("Domain error: {0}")]
pub struct DomainError(pub String);

/// Error envelope type
#[derive(Debug, Clone)]
pub struct ErrorEnvelope {
    pub message: String,
    pub code: u32,
}

/// Repository error type
#[derive(Error, Debug, Clone)]
#[error("Repository error: {0}")]
pub struct RepositoryError(pub String);

/// Storage error type
#[derive(Error, Debug, Clone)]
#[error("Storage error: {0}")]
pub struct StorageError(pub String);

/// Result type alias
pub type Result<T> = std::result::Result<T, PhenotypeError>;
