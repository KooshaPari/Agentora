//! # Phenotype Errors (DEPRECATED)
//!
//! This crate is deprecated. Use `phenotype-error-core` directly.
//!
//! ```toml
//! [dependencies]
//! phenotype-error-core = "0.2"
//! ```
//!
//! ## Migration
//!
//! Replace `phenotype-errors` with `phenotype-error-core` in your Cargo.toml,
//! then update imports:
//!
//! ```rust,ignore
//! // Old
//! use phenotype_errors::{ApiError, Result};
//!
//! // New
//! use phenotype_error_core::{ApiError, Result};
//! ```

#![deprecated(
    since = "0.2.0",
    note = "Use phenotype-error-core directly instead"
)]

pub use phenotype_error_core::{
    ApiError, ConfigError, DomainError, ErrorEnvelope, RepositoryError, StorageError,
};

/// Canonical error type alias.
#[deprecated(since = "0.2.0", note = "Use phenotype_error_core::Error instead")]
pub type Error = ApiError;

/// Convenience result type.
#[deprecated(since = "0.2.0", note = "Use phenotype_error_core::Result instead")]
pub type Result<T> = std::result::Result<T, ApiError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_api_error() {
        let err = ApiError::NotFound {
            resource: "user".into(),
            id: "42".into(),
        };
        assert_eq!(err.status_code(), 404);
    }

    #[test]
    fn test_result_type_ok() {
        let r: Result<i32> = Ok(42);
        assert_eq!(r.unwrap(), 42);
    }

    #[test]
    fn test_domain_error() {
        let err = DomainError::Validation("invalid".into());
        assert!(err.to_string().contains("validation failed"));
    }
}
