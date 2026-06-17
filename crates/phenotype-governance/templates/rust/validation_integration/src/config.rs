//! Configuration with validation
//!
//! Demonstrates using phenotype-validation for configuration validation.

use phenotype_validation::{Result, ValidationResult, Validator};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Application name
    pub name: String,
    /// Application version
    pub version: String,
    /// Server configuration
    pub server: ServerConfig,
    /// Database configuration
    pub database: DatabaseConfig,
    /// Optional features
    pub features: Option<Vec<String>>,
}

/// Server configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    /// Host to bind to
    pub host: String,
    /// Port to listen on
    pub port: u16,
    /// TLS configuration
    pub tls: Option<TlsConfig>,
}

/// Database configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    /// Database URL
    pub url: String,
    /// Connection pool size
    pub pool_size: u32,
    /// Timeout in seconds
    pub timeout: u64,
}

/// TLS configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TlsConfig {
    /// Certificate file path
    pub cert: String,
    /// Key file path
    pub key: String,
}

/// Creates a validator for AppConfig
fn create_app_validator() -> Validator {
    Validator::new()
        .required("name")
        .string("name")
        .min_length("name", 1)
        .required("version")
        .string("version")
        .pattern("version", r"^\d+\.\d+\.\d+(-.+)?$")
        .required("server")
        .object("server")
        .required("database")
        .object("database")
}

/// Validates AppConfig
pub fn validate_app_config(config: &AppConfig) -> Result<ValidationResult> {
    let validator = create_app_validator();
    let json = serde_json::to_value(config).unwrap();

    let mut result = validator.validate(&json)?;

    // Validate nested server config
    let server_result = validate_server_config(&config.server)?;
    if !server_result.is_valid {
        for error in server_result.errors {
            result.add_error(error);
        }
    }

    // Validate nested database config
    let db_result = validate_database_config(&config.database)?;
    if !db_result.is_valid {
        for error in db_result.errors {
            result.add_error(error);
        }
    }

    Ok(result)
}

/// Validates ServerConfig
fn validate_server_config(config: &ServerConfig) -> Result<ValidationResult> {
    let validator = Validator::new()
        .required("host")
        .string("host")
        .pattern("host", r"^[\w.-]+$")
        .required("port")
        .integer("port")
        .min(1.0)
        .max(65535.0);

    let json = serde_json::to_value(config).unwrap();
    validator.validate(&json)
}

/// Validates DatabaseConfig
fn validate_database_config(config: &DatabaseConfig) -> Result<ValidationResult> {
    let validator = Validator::new()
        .required("url")
        .string("url")
        .pattern("url", r"^(postgres|mysql|sqlite)://")
        .required("pool_size")
        .integer("pool_size")
        .min(1.0)
        .max(100.0)
        .required("timeout")
        .integer("timeout")
        .min(1.0)
        .max(300.0);

    let json = serde_json::to_value(config).unwrap();
    validator.validate(&json)
}

/// Loads and validates configuration from file
pub fn load_config(path: &str) -> Result<AppConfig, Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(path)?;
    let config: AppConfig = toml::from_str(&content)?;

    let validation = validate_app_config(&config)?;
    if !validation.is_valid {
        let errors: Vec<String> = validation.errors.iter().map(|e| e.to_string()).collect();
        return Err(format!("Configuration validation failed:\n{}", errors.join("\n")).into());
    }

    Ok(config)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_config() {
        let config = AppConfig {
            name: "my-app".to_string(),
            version: "1.0.0".to_string(),
            server: ServerConfig {
                host: "localhost".to_string(),
                port: 8080,
                tls: None,
            },
            database: DatabaseConfig {
                url: "postgres://localhost/mydb".to_string(),
                pool_size: 10,
                timeout: 30,
            },
            features: None,
        };

        let result = validate_app_config(&config).unwrap();
        assert!(result.is_valid);
    }

    #[test]
    fn test_invalid_name() {
        let config = AppConfig {
            name: "".to_string(),
            version: "1.0.0".to_string(),
            server: ServerConfig {
                host: "localhost".to_string(),
                port: 8080,
                tls: None,
            },
            database: DatabaseConfig {
                url: "postgres://localhost/mydb".to_string(),
                pool_size: 10,
                timeout: 30,
            },
            features: None,
        };

        let result = validate_app_config(&config).unwrap();
        assert!(!result.is_valid);
    }

    #[test]
    fn test_invalid_version() {
        let config = AppConfig {
            name: "my-app".to_string(),
            version: "not-a-version".to_string(),
            server: ServerConfig {
                host: "localhost".to_string(),
                port: 8080,
                tls: None,
            },
            database: DatabaseConfig {
                url: "postgres://localhost/mydb".to_string(),
                pool_size: 10,
                timeout: 30,
            },
            features: None,
        };

        let result = validate_app_config(&config).unwrap();
        assert!(!result.is_valid);
    }

    #[test]
    fn test_invalid_port() {
        let config = AppConfig {
            name: "my-app".to_string(),
            version: "1.0.0".to_string(),
            server: ServerConfig {
                host: "localhost".to_string(),
                port: 70000, // Invalid port
                tls: None,
            },
            database: DatabaseConfig {
                url: "postgres://localhost/mydb".to_string(),
                pool_size: 10,
                timeout: 30,
            },
            features: None,
        };

        let result = validate_app_config(&config).unwrap();
        assert!(!result.is_valid);
    }

    #[test]
    fn test_invalid_database_url() {
        let config = AppConfig {
            name: "my-app".to_string(),
            version: "1.0.0".to_string(),
            server: ServerConfig {
                host: "localhost".to_string(),
                port: 8080,
                tls: None,
            },
            database: DatabaseConfig {
                url: "invalid://localhost/mydb".to_string(),
                pool_size: 10,
                timeout: 30,
            },
            features: None,
        };

        let result = validate_app_config(&config).unwrap();
        assert!(!result.is_valid);
    }
}
