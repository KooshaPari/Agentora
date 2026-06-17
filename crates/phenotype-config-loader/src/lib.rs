//! Configuration loading utilities for Phenotype
//!
//! Supports loading configs from TOML, YAML, JSON, and environment variables.

use serde::de::DeserializeOwned;
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;

/// Configuration loading errors
#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("TOML parse error: {0}")]
    Toml(#[from] toml::de::Error),
    #[error("JSON parse error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("YAML parse error: {0}")]
    Yaml(String),
    #[error("Unsupported format: {0}")]
    UnsupportedFormat(String),
    #[error("Config not found: {0}")]
    NotFound(String),
}

/// Result type for config operations
pub type Result<T> = std::result::Result<T, ConfigError>;

/// Configuration file formats
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfigFormat {
    /// TOML format
    Toml,
    /// YAML format
    Yaml,
    /// JSON format
    Json,
}

impl ConfigFormat {
    /// Detect format from file extension
    pub fn from_path<P: AsRef<Path>>(path: P) -> Option<Self> {
        let ext = path.as_ref().extension()?.to_str()?;
        match ext.to_lowercase().as_str() {
            "toml" => Some(Self::Toml),
            "yaml" | "yml" => Some(Self::Yaml),
            "json" => Some(Self::Json),
            _ => None,
        }
    }
}

/// Load configuration from a file
pub fn load_from_file<T: DeserializeOwned, P: AsRef<Path>>(path: P) -> Result<T> {
    let content = std::fs::read_to_string(&path)?;
    let format = ConfigFormat::from_path(&path)
        .ok_or_else(|| ConfigError::UnsupportedFormat(
            path.as_ref().to_string_lossy().to_string()
        ))?;
    
    parse_config(&content, format)
}

/// Parse configuration from a string
pub fn parse_config<T: DeserializeOwned>(content: &str, format: ConfigFormat) -> Result<T> {
    match format {
        ConfigFormat::Toml => {
            let value: T = toml::from_str(content)?;
            Ok(value)
        }
        ConfigFormat::Json => {
            let value: T = serde_json::from_str(content)?;
            Ok(value)
        }
        ConfigFormat::Yaml => {
            serde_yaml::from_str(content)
                .map_err(|e| ConfigError::Yaml(e.to_string()))
        }
    }
}

/// Load from environment variables with prefix
pub fn from_env<T: DeserializeOwned>(prefix: &str) -> Result<T> {
    let vars: HashMap<String, String> = std::env::vars()
        .filter(|(k, _)| k.starts_with(prefix))
        .map(|(k, v)| (k.trim_start_matches(prefix).to_lowercase(), v))
        .collect();
    
    let json = serde_json::to_string(&vars)
        .map_err(ConfigError::Json)?;
    serde_json::from_str(&json).map_err(ConfigError::Json)
}

/// Configuration loader with builder pattern
#[derive(Debug)]
pub struct ConfigLoader<T: DeserializeOwned> {
    file_path: Option<String>,
    env_prefix: Option<String>,
    _phantom: std::marker::PhantomData<T>,
}

impl<T: DeserializeOwned + Default> Default for ConfigLoader<T> {
    fn default() -> Self {
        Self::new()
    }
}

impl<T: DeserializeOwned> ConfigLoader<T> {
    /// Create a new config loader
    pub fn new() -> Self {
        Self {
            file_path: None,
            env_prefix: None,
            _phantom: std::marker::PhantomData,
        }
    }
    
    /// Set file path to load from
    pub fn with_file(mut self, path: impl Into<String>) -> Self {
        self.file_path = Some(path.into());
        self
    }
    
    /// Set environment variable prefix
    pub fn with_env_prefix(mut self, prefix: impl Into<String>) -> Self {
        self.env_prefix = Some(prefix.into());
        self
    }
    
    /// Load configuration
    pub fn load(self) -> Result<T> {
        if let Some(path) = self.file_path {
            load_from_file(&path)
        } else if let Some(prefix) = self.env_prefix {
            from_env(&prefix)
        } else {
            Err(ConfigError::NotFound("No source specified".to_string()))
        }
    }
}

/// Load and merge multiple config sources
pub fn merge_configs<T: DeserializeOwned + serde::Serialize>(
    sources: Vec<(String, ConfigFormat)>,
) -> Result<T> {
    let mut merged = serde_json::Map::new();
    
    for (content, format) in sources {
        let value: serde_json::Value = parse_config(&content, format)?;
        if let serde_json::Value::Object(map) = value {
            for (k, v) in map {
                merged.insert(k, v);
            }
        }
    }
    
    let json = serde_json::Value::Object(merged);
    serde_json::from_value(json).map_err(ConfigError::Json)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::Deserialize;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[derive(Debug, Deserialize, Serialize, PartialEq)]
    struct TestConfig {
        name: String,
        value: i32,
    }

    #[test]
    fn test_parse_toml() {
        let toml = r#"name = "test"
value = 42
"#;
        let config: TestConfig = parse_config(toml, ConfigFormat::Toml).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
    }

    #[test]
    fn test_parse_json() {
        let json = r#"{"name": "test", "value": 42}"#;
        let config: TestConfig = parse_config(json, ConfigFormat::Json).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
    }

    #[test]
    fn test_load_from_file() -> Result<()> {
        let mut file = NamedTempFile::new()?;
        write!(file, r#"{{"name": "test", "value": 42}}"#)?;
        
        let config: TestConfig = load_from_file(file.path())?;
        assert_eq!(config.name, "test");
        Ok(())
    }

    #[test]
    fn test_config_format_from_path() {
        assert_eq!(ConfigFormat::from_path("config.toml"), Some(ConfigFormat::Toml));
        assert_eq!(ConfigFormat::from_path("config.yaml"), Some(ConfigFormat::Yaml));
        assert_eq!(ConfigFormat::from_path("config.json"), Some(ConfigFormat::Json));
        assert_eq!(ConfigFormat::from_path("config.txt"), None);
    }
}
