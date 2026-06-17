//! phenotype-port-traits

use thiserror::Error;

pub mod inbound;
pub mod outbound;
pub mod observability;

// Re-export observability traits for convenience
pub use observability::{CounterMetrics, MetricsHook, NoOpMetrics};
#[derive(Debug, Error)]
pub enum Error {
    #[error("{0}")]
    Invalid(String),
}

pub type Result<T> = std::result::Result<T, Error>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn error_display() {
        let err = Error::Invalid("bad input".into());
        assert_eq!(err.to_string(), "bad input");
    }

    #[test]
    fn error_debug() {
        let err = Error::Invalid("x".into());
        let debug = format!("{:?}", err);
        assert!(debug.contains("Invalid"));
        assert!(debug.contains("x"));
    }

    #[test]
    fn result_ok() {
        let val: Result<i32> = Ok(42);
        assert_eq!(val.unwrap(), 42);
    }

    #[test]
    fn result_err() {
        let val: Result<i32> = Err(Error::Invalid("fail".into()));
        assert!(val.is_err());
    }
}
