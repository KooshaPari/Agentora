//! Validation framework for Phenotype with hexagonal architecture

#![allow(missing_docs)]

pub mod error;
pub mod ports;
pub mod rules;
pub mod types;

pub use error::{Result, ValidationError};
pub use ports::ValidatorPort;
pub use rules::{Condition, JsonType, Operator, Rule, RuleEngine};
pub use types::{Severity, ValidationContext, ValidationIssue, ValidationResult};

pub mod prelude {
    pub use crate::error::{Result, ValidationError};
    pub use crate::ports::ValidatorPort;
    pub use crate::rules::{Condition, JsonType, Operator, Rule, RuleEngine};
    pub use crate::types::{Severity, ValidationContext, ValidationIssue, ValidationResult};
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_result_success() {
        let result = ValidationResult::success();
        assert!(result.is_valid);
    }

    #[test]
    fn test_validation_result_failure() {
        let result = ValidationResult::failure("test");
        assert!(!result.is_valid);
    }
}
