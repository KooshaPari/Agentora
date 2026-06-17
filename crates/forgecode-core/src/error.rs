use thiserror::Error;

#[derive(Debug, Clone, Error)]
pub enum ForgecodeError {
    #[error("provider not found: {0}")]
    ProviderNotFound(String),

    #[error("agent not found: {0}")]
    AgentNotFound(String),

    #[error("invalid config: {0}")]
    InvalidConfig(String),

    #[error("provider error: {0}")]
    ProviderError(String),
}

pub type Result<T> = std::result::Result<T, ForgecodeError>;
