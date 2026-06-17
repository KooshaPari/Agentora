//! Configuration management

use std::collections::HashMap;

/// Configuration container
#[derive(Debug, Clone, Default)]
pub struct Config {
    values: HashMap<String, String>,
}

impl Config {
    /// Create a new empty config
    pub fn new() -> Self {
        Self {
            values: HashMap::new(),
        }
    }
    
    /// Get a configuration value
    pub fn get(&self, key: &str) -> Option<&String> {
        self.values.get(key)
    }
    
    /// Set a configuration value
    pub fn set(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.values.insert(key.into(), value.into());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_config() {
        let mut config = Config::new();
        config.set("key", "value");
        assert_eq!(config.get("key"), Some(&"value".to_string()));
    }
}
