//! Domain errors

use thiserror::Error;

/// Domain-level errors
#[derive(Debug, Error)]
pub enum DomainError {
    #[error("Invalid command: {0}")]
    InvalidCommand(String),

    #[error("Missing required argument: {0}")]
    MissingArgument(String),

    #[error("Invalid argument value: {0}")]
    InvalidArgument(String),

    #[error("Command not found: {0}")]
    CommandNotFound(String),

    #[error("Validation failed: {0}")]
    ValidationFailed(String),

    #[error("Plugin error: {0}")]
    PluginError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("IO error: {0}")]
    IoError(String),
}

impl From<std::io::Error> for DomainError {
    fn from(err: std::io::Error) -> Self {
        DomainError::IoError(err.to_string())
    }
}

impl From<serde_json::Error> for DomainError {
    fn from(err: serde_json::Error) -> Self {
        DomainError::ConfigError(err.to_string())
    }
}
