//! Domain errors

use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("Agent error: {0}")]
    Agent(String),

    #[error("Skill error: {0}")]
    Skill(String),

    #[error("Tool error: {0}")]
    Tool(String),

    #[error("Memory error: {0}")]
    Memory(String),

    #[error("LLM error: {0}")]
    LLM(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Execution error: {0}")]
    Execution(String),
}

pub type Result<T> = std::result::Result<T, Error>;
