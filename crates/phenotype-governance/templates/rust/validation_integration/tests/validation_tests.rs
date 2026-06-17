//! Validation tests

use phenotype_validation::{Result, Validator};
use serde_json::json;

#[test]
fn test_basic_validation() {
    let validator = Validator::new()
        .required("name")
        .string("name")
        .min_length("name", 1);

    let data = json!({"name": "Test"});
    let result = validator.validate(&data).unwrap();

    assert!(result.is_valid);
}

#[test]
fn test_email_validation() {
    let validator = Validator::new().required("email").email();

    let valid = json!({"email": "test@example.com"});
    let result = validator.validate(&valid).unwrap();
    assert!(result.is_valid);

    let invalid = json!({"email": "not-an-email"});
    let result = validator.validate(&invalid).unwrap();
    assert!(!result.is_valid);
}

#[test]
fn test_numeric_range() {
    let validator = Validator::new()
        .required("age")
        .integer("age")
        .min(0.0)
        .max(150.0);

    let valid = json!({"age": 30});
    let result = validator.validate(&valid).unwrap();
    assert!(result.is_valid);

    let too_high = json!({"age": 200});
    let result = validator.validate(&too_high).unwrap();
    assert!(!result.is_valid);
}

#[test]
fn test_multiple_errors() {
    let validator = Validator::new().required("name").required("email").email();

    let data = json!({});
    let result = validator.validate(&data).unwrap();

    assert!(!result.is_valid);
    assert!(result.error_count() >= 2);
}

#[test]
fn test_pattern_matching() {
    let validator = Validator::new()
        .required("phone")
        .pattern("phone", r"^\d{3}-\d{3}-\d{4}$");

    let valid = json!({"phone": "555-123-4567"});
    let result = validator.validate(&valid).unwrap();
    assert!(result.is_valid);

    let invalid = json!({"phone": "5551234567"});
    let result = validator.validate(&invalid).unwrap();
    assert!(!result.is_valid);
}

#[test]
fn test_enum_validation() {
    let validator = Validator::new()
        .required("status")
        .one_of(vec!["active", "inactive", "pending"]);

    let valid = json!({"status": "active"});
    let result = validator.validate(&valid).unwrap();
    assert!(result.is_valid);

    let invalid = json!({"status": "deleted"});
    let result = validator.validate(&invalid).unwrap();
    assert!(!result.is_valid);
}
