//! Example plugin implementation demonstrating the Plugin trait.
//!
//! This can serve as a template for plugin authors.

use crate::domain::{Command, Plugin, Result};

/// Echo plugin — adds an `echo` command that repeats its arguments.
pub struct EchoPlugin;

impl Plugin for EchoPlugin {
    fn name(&self) -> &str {
        "echo"
    }

    fn version(&self) -> &str {
        "0.1.0"
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

/// Construct the example echo plugin.
pub fn create() -> Box<dyn Plugin> {
    Box::new(EchoPlugin)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_echo_plugin_name() {
        let p = EchoPlugin;
        assert_eq!(p.name(), "echo");
    }

    #[test]
    fn test_echo_plugin_version() {
        let p = EchoPlugin;
        assert_eq!(p.version(), "0.1.0");
    }

    #[test]
    fn test_echo_plugin_init() {
        let p = EchoPlugin;
        assert!(p.init().is_ok());
    }

    #[test]
    fn test_echo_plugin_commands_empty() {
        let p = EchoPlugin;
        assert!(p.commands().is_empty());
    }
}
