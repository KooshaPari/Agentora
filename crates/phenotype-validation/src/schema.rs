//! Schema validation

use std::collections::HashMap;

/// Schema validation error
#[derive(Debug, thiserror::Error)]
pub enum SchemaValidationError {
    #[error("Missing required field: {0}")]
    MissingField(String),
    #[error("Invalid type for field: {0}")]
    InvalidType(String),
    #[error("Field validation failed: {0} - {1}")]
    FieldError(String, String),
}

/// Schema definition for validation
#[derive(Clone, Debug)]
pub struct Schema {
    fields: HashMap<String, FieldType>,
    required: Vec<String>,
}

impl Schema {
    pub fn new() -> Self {
        Self {
            fields: HashMap::new(),
            required: Vec::new(),
        }
    }

    pub fn with_field(mut self, name: &str, field_type: FieldType) -> Self {
        self.fields.insert(name.to_string(), field_type);
        self
    }

    pub fn with_required(mut self, name: &str) -> Self {
        self.required.push(name.to_string());
        self
    }

    /// Validate data against schema
    pub fn validate(&self, data: &HashMap<String, serde_json::Value>) -> Result<(), SchemaValidationError> {
        for field in &self.required {
            if !data.contains_key(field) {
                return Err(SchemaValidationError::MissingField(field.clone()));
            }
        }
        Ok(())
    }
}

impl Default for Schema {
    fn default() -> Self {
        Self::new()
    }
}

/// Field types for schema
#[derive(Debug, Clone)]
pub enum FieldType {
    String,
    Integer,
    Boolean,
    Array(Box<FieldType>),
    Object(Box<Schema>),
}
