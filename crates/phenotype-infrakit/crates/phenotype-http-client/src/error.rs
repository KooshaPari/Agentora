//! HTTP client error types

use thiserror::Error;

#[derive(Error, Debug)]
pub enum HttpError {
    #[error(\"request failed: {0}\")]
    Request(#[from] reqwest::Error),
    #[error(\"status error: {0}\")]
    Status(u16),
    #[error(\"serialization error: {0}\")]
    Serialization(#[from] serde_json::Error),
    #[error(\"unknown error: {0}\")]
    Unknown(String),
}

pub type Result<T> = std::result::Result<T, HttpError>;
