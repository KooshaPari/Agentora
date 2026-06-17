# Data Validation
#
# Traces to: FR-VAL-001, FR-VAL-002, FR-VAL-003

Feature: Data Validation
  As a developer
  I want to validate data structures
  So that I can ensure data integrity

  Background:
    Given a validator is configured

  Scenario: Validate required fields
    Given the validator requires field "name"
    When I validate data:
      """json
      {"name": "John"}
      """
    Then validation should pass
    
    When I validate data:
      """json
      {}
      """
    Then validation should fail
    And the error should mention "name is required"

  Scenario: Validate string type
    Given the validator expects "email" to be a string
    When I validate data:
      """json
      {"email": "test@example.com"}
      """
    Then validation should pass
    
    When I validate data:
      """json
      {"email": 123}
      """
    Then validation should fail
    And the error should mention "expected string"

  Scenario: Validate email format
    Given the validator expects "email" to be a valid email
    When I validate data:
      """json
      {"email": "valid@example.com"}
      """
    Then validation should pass
    
    When I validate data:
      """json
      {"email": "invalid-email"}
      """
    Then validation should fail
    And the error should mention "invalid email"

  Scenario: Validate numeric range
    Given the validator expects "age" to be between 0 and 150
    When I validate data:
      """json
      {"age": 30}
      """
    Then validation should pass
    
    When I validate data:
      """json
      {"age": 200}
      """
    Then validation should fail
    And the error should mention "must be at most 150"

  Scenario: Validate string length
    Given the validator expects "password" to have minimum length 8
    When I validate data:
      """json
      {"password": "secure123"}
      """
    Then validation should pass
    
    When I validate data:
      """json
      {"password": "short"}
      """
    Then validation should fail
    And the error should mention "length must be at least 8"

  Scenario: Validate enum values
    Given the validator expects "status" to be one of ["active", "inactive", "pending"]
    When I validate data:
      """json
      {"status": "active"}
      """
    Then validation should pass
    
    When I validate data:
      """json
      {"status": "deleted"}
      """
    Then validation should fail
    And the error should mention "must be one of"

  Scenario: Validate with regex pattern
    Given the validator expects "phone" to match pattern "^\\d{3}-\\d{3}-\\d{4}$"
    When I validate data:
      """json
      {"phone": "555-123-4567"}
      """
    Then validation should pass
    
    When I validate data:
      """json
      {"phone": "5551234567"}
      """
    Then validation should fail
    And the error should mention "does not match pattern"

  Scenario: Validate nested objects
    Given the validator expects "user" to be an object with:
      | field | type   | required |
      | name  | string | yes      |
      | age   | number | no       |
    When I validate data:
      """json
      {
        "user": {
          "name": "John",
          "age": 30
        }
      }
      """
    Then validation should pass
    
    When I validate data:
      """json
      {
        "user": {
          "age": 30
        }
      }
      """
    Then validation should fail
    And the error should mention "name is required"

  Scenario: Multiple validation errors
    Given the validator:
      | field    | rule              |
      | name     | required          |
      | email    | email             |
      | age      | range(0,150)       |
    When I validate invalid data
    Then validation should fail
    And there should be multiple errors
    And each error should specify the field

  @schema
  Scenario: Validate with JSON Schema
    Given a JSON Schema:
      """json
      {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "age": {"type": "integer", "minimum": 0}
        },
        "required": ["name"]
      }
      """
    When I validate data against the schema
    Then the result should indicate schema compliance
