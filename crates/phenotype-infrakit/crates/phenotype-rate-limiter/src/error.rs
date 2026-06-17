//! Error types for rate limiting

use thiserror::Error;

/// Result type alias
pub type Result<T> = std::result::Result<T, RateLimitError>;

/// Rate limit errors
#[derive(Error, Debug, Clone, PartialEq)]
pub enum RateLimitError {
    #[error("rate limit exceeded for key '{key}', retry after {retry_after:?}")]
    Exceeded {
        key: String,
        retry_after: std::time::Duration,
        limit: u32,
    },

    #[error("invalid configuration: {message}")]
    InvalidConfig { message: String },

    #[error("rate limited, retry after {retry_after_ms}ms")]
    RateLimited { retry_after_ms: u64 },

    #[error("backend error: {0}")]
    BackendError(String),

    #[error("config error: {0}")]
    ConfigError(String),
}

impl RateLimitError {
    pub fn exceeded(key: impl Into<String>, retry_after: std::time::Duration, limit: u32) -> Self {
        Self::Exceeded {
            key: key.into(),
            retry_after,
            limit,
        }
    }

    pub fn invalid_config(message: impl Into<String>) -> Self {
        Self::InvalidConfig {
            message: message.into(),
        }
    }

    pub fn is_exceeded(&self) -> bool {
        matches!(self, Self::Exceeded { .. } | Self::RateLimited { .. })
    }

    pub fn retry_after(&self) -> Option<std::time::Duration> {
        match self {
            Self::Exceeded { retry_after, .. } => Some(*retry_after),
            Self::RateLimited { retry_after_ms } => {
                Some(std::time::Duration::from_millis(*retry_after_ms))
            }
            _ => None,
        }
    }
}
