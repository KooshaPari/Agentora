//! Validator builder and execution
//!
//! Provides a fluent API for building validators and executing validation.

use crate::{
    error::{Result, ValidationError},
    rules::{Condition, Rule, RuleEngine},
    types::{Severity, ValidationContext, ValidationIssue, ValidationResult},
};
use serde_json::Value;

/// Main validator for executing validation rules
#[derive(Debug, Clone)]
pub struct Validator {
    engine: RuleEngine,
}

impl Validator {
    /// Create a new empty validator
    pub fn new() -> Self {
        Self {
            engine: RuleEngine::new(),
        }
    }

    /// Add a rule to the validator
    pub fn add_rule(mut self, rule: Rule) -> Self {
        self.engine.add_rule(rule);
        self
    }

    /// Validate data against all rules
    pub fn validate(&self, data: &Value) -> ValidationResult {
        let ctx = ValidationContext::from_json(data.clone());
        self.engine.evaluate(&ctx)
    }

    /// Check if data is valid (convenience method)
    pub fn is_valid(&self, data: &Value) -> bool {
        self.validate(data).is_valid()
    }
}

impl Default for Validator {
    fn default() -> Self {
        Self::new()
    }
}

/// Builder for constructing validators fluently
#[derive(Debug)]
pub struct ValidatorBuilder {
    rules: Vec<Rule>,
    current_field: Option<String>,
}

impl ValidatorBuilder {
    /// Create a new validator builder
    pub fn new() -> Self {
        Self {
            rules: Vec::new(),
            current_field: None,
        }
    }

    /// Start defining rules for a field
    pub fn field(mut self, name: impl Into<String>) -> Self {
        self.current_field = Some(name.into());
        self
    }

    /// Add a required rule for the current field
    pub fn required(mut self) -> Self {
        if let Some(field) = &self.current_field {
            self.rules.push(
                Rule::new(
                    format!("{}_required", field),
                    field.clone(),
                    Condition::Required,
                )
                .with_message(format!("{} is required", field)),
            );
        }
        self
    }

    /// Add a type rule for the current field
    pub fn type_check(mut self, expected: crate::rules::JsonType) -> Self {
        if let Some(field) = &self.current_field {
            self.rules.push(Rule::new(
                format!("{}_type", field),
                field.clone(),
                Condition::Type { expected },
            ));
        }
        self
    }

    /// Add a not-empty rule for the current field
    pub fn not_empty(mut self) -> Self {
        if let Some(field) = &self.current_field {
            self.rules.push(Rule::new(
                format!("{}_not_empty", field),
                field.clone(),
                Condition::NotEmpty,
            ));
        }
        self
    }

    /// Build the validator
    pub fn build(self) -> Validator {
        let mut engine = RuleEngine::new();
        for rule in self.rules {
            engine.add_rule(rule);
        }
        Validator { engine }
    }
}

impl Default for ValidatorBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_validator_creation() {
        let validator = Validator::new();
        let data = json!({"name": "test"});
        assert!(validator.is_valid(&data));
    }

    #[test]
    fn test_validator_builder() {
        let validator = ValidatorBuilder::new().field("name").required().build();

        let valid_data = json!({"name": "test"});
        assert!(validator.is_valid(&valid_data));

        let invalid_data = json!({});
        assert!(!validator.is_valid(&invalid_data));
    }

    #[test]
    fn test_add_rule() {
        let validator = Validator::new().add_rule(Rule::new("test", "field", Condition::Required));

        let data = json!({"field": "value"});
        let outcome = validator.validate(&data);
        assert!(outcome.is_valid());
    }
}
