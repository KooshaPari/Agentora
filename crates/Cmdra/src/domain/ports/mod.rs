//! Domain ports - Interfaces for adapters
//!
//! Ports define the interfaces that adapters must implement.
//! This follows the hexagonal architecture pattern.

use super::{Command, Context, Input, Output, Result};
use async_trait::async_trait;

/// Inbound port for command execution
#[async_trait]
pub trait CommandExecutor: Send + Sync {
    /// Execute a command with the given input
    async fn execute(&self, command: &Command, input: Input) -> Result<Output>;
}

/// Inbound port for command handlers
#[async_trait]
pub trait CommandHandler: Send + Sync {
    /// Handle a command execution
    async fn handle(&self, ctx: &Context) -> Result<Output>;

    /// Validate input before handling
    fn validate(&self, _input: &Input) -> Result<()> {
        Ok(())
    }
}

/// Outbound port for configuration loading
pub trait ConfigLoader: Send + Sync {
    /// Load configuration
    fn load(&self) -> Result<serde_json::Value>;

    /// Get a specific config value
    fn get(&self, key: &str) -> Result<Option<serde_json::Value>>;
}

/// Outbound port for output formatting
pub trait OutputFormatter: Send + Sync {
    /// Format output
    fn format(&self, output: Output) -> String;
}

/// Outbound port for logging
pub trait Logger: Send + Sync {
    /// Log at info level
    fn info(&self, msg: &str);

    /// Log at debug level
    fn debug(&self, msg: &str);

    /// Log at warn level
    fn warn(&self, msg: &str);

    /// Log at error level
    fn error(&self, msg: &str);
}

/// Outbound port for plugin loading
pub trait PluginLoader: Send + Sync {
    /// Load plugins from directory
    fn load_dir(&self, path: &std::path::Path) -> Result<Vec<Box<dyn Plugin>>>;

    /// Load a specific plugin
    fn load_plugin(&self, path: &std::path::Path) -> Result<Box<dyn Plugin>>;
}

/// Plugin trait for extensibility
pub trait Plugin: Send + Sync {
    /// Get plugin name
    fn name(&self) -> &str;

    /// Get plugin version
    fn version(&self) -> &str;

    /// Initialize the plugin
    fn init(&self) -> Result<()>;

    /// Get commands provided by this plugin
    fn commands(&self) -> Vec<Command>;

    /// Cleanup when unloading
    fn cleanup(&self) -> Result<()>;
}

/// Outbound port for telemetry
pub trait Telemetry: Send + Sync {
    /// Record a command execution
    fn record_execution(&self, command: &str, duration_ms: u64, success: bool);

    /// Record an error
    fn record_error(&self, command: &str, error: &str);

    /// Record a metric
    fn record_metric(&self, name: &str, value: f64);
}

/// Inbound port for CLI parsing
pub trait CliParser: Send + Sync {
    /// Parse command line arguments
    fn parse(&self, args: Vec<String>) -> Result<Input>;

    /// Format help text
    fn format_help(&self, command: &Command) -> String;
}

/// Outbound port for persistence
pub trait Persistence: Send + Sync {
    /// Save state
    fn save(&self, key: &str, value: &[u8]) -> Result<()>;

    /// Load state
    fn load(&self, key: &str) -> Result<Option<Vec<u8>>>;

    /// Delete state
    fn delete(&self, key: &str) -> Result<()>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::entities::Command;

    struct TestPlugin;

    impl Plugin for TestPlugin {
        fn name(&self) -> &str {
            "test-plugin"
        }
        fn version(&self) -> &str {
            "1.0.0"
        }
        fn init(&self) -> Result<()> {
            Ok(())
        }
        fn commands(&self) -> Vec<Command> {
            vec![]
        }
        fn cleanup(&self) -> Result<()> {
            Ok(())
        }
    }

    #[test]
    fn test_plugin_trait() {
        let plugin = TestPlugin;
        assert_eq!(plugin.name(), "test-plugin");
    }
}
