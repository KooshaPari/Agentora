//! Error handling infrastructure

use thiserror::Error;

#[derive(Debug, Error)]
pub enum CliError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Parse error: {0}")]
    Parse(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Plugin error: {0}")]
    Plugin(String),

    #[error("Config error: {0}")]
    Config(String),

    #[error("Execution error: {0}")]
    Execution(String),
}

pub type Result<T> = std::result::Result<T, CliError>;
