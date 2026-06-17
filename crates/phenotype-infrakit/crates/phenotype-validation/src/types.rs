//! Validation types and result structures

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    /// Error - validation failed
    #[default]
    Error,
    /// Warning - validation passed with warning
    Warning,
    /// Info - informational only
    Info,
}

#[derive(Debug, Clone)]
pub struct ValidationIssue {
    pub severity: Severity,
    pub path: String,
    pub code: String,
    pub message: String,
}

impl ValidationIssue {
    pub fn error(code: &str, message: &str) -> Self {
        Self {
            severity: Severity::Error,
            path: String::new(),
            code: code.to_string(),
            message: message.to_string(),
        }
    }

    pub fn warning(code: &str, message: &str) -> Self {
        Self {
            severity: Severity::Warning,
            path: String::new(),
            code: code.to_string(),
            message: message.to_string(),
        }
    }

    pub fn with_path(mut self, path: impl Into<String>) -> Self {
        self.path = path.into();
        self
    }

    pub fn is_error(&self) -> bool {
        matches!(self.severity, Severity::Error)
    }
}

#[derive(Debug, Clone, Default)]
pub struct ValidationResult {
    pub is_valid: bool,
    pub errors: Vec<ValidationIssue>,
    pub warnings: Vec<ValidationIssue>,
}

impl ValidationResult {
    pub fn success() -> Self {
        Self {
            is_valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
        }
    }

    pub fn failure(message: &str) -> Self {
        Self {
            is_valid: false,
            errors: vec![ValidationIssue::error("validation_failed", message)],
            warnings: Vec::new(),
        }
    }

    pub fn add_error(&mut self, issue: ValidationIssue) {
        self.is_valid = false;
        self.errors.push(issue);
    }

    pub fn add_warning(&mut self, issue: ValidationIssue) {
        self.warnings.push(issue);
    }

    pub fn merge(&mut self, other: ValidationResult) {
        if !other.is_valid {
            self.is_valid = false;
        }
        self.errors.extend(other.errors);
        self.warnings.extend(other.warnings);
    }
}

#[derive(Debug, Clone)]
pub struct ValidationContext {
    data: serde_json::Value,
}

impl ValidationContext {
    pub fn from_json(value: serde_json::Value) -> Self {
        Self { data: value }
    }

    pub fn from_data<T: serde::Serialize>(
        data: &T,
    ) -> std::result::Result<Self, crate::error::ValidationError> {
        let value = serde_json::to_value(data)
            .map_err(|e| crate::error::ValidationError::Serialization(e.to_string()))?;
        Ok(Self { data: value })
    }

    pub fn get_path(&self, path: &str) -> Option<&serde_json::Value> {
        let mut current = &self.data;
        for key in path.split('.') {
            match current {
                serde_json::Value::Object(map) => current = map.get(key)?,
                _ => return None,
            }
        }
        Some(current)
    }

    pub fn data(&self) -> &serde_json::Value {
        &self.data
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_result_success() {
        let result = ValidationResult::success();
        assert!(result.is_valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn test_validation_result_failure() {
        let result = ValidationResult::failure("test error");
        assert!(!result.is_valid);
        assert_eq!(result.errors.len(), 1);
    }

    #[test]
    fn test_validation_issue_error() {
        let issue = ValidationIssue::error("code", "message");
        assert!(issue.is_error());
    }

    #[test]
    fn test_validation_context_get_path() {
        let ctx = ValidationContext::from_json(serde_json::json!({
            "user": { "name": "John" }
        }));
        assert_eq!(ctx.get_path("user.name").unwrap().as_str(), Some("John"));
    }
}
