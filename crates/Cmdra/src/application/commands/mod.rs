//! Command handlers - Write operations
//!
//! Commands represent write operations in the application.

use crate::domain::{Command, CommandHandler, CommandRegistry, Context, Output, Result};
use async_trait::async_trait;

/// Default command handler implementation
pub struct DefaultHandler<F, Fut>
where
    F: Fn(&Context) -> Fut,
    Fut: std::future::Future<Output = Result<Output>>,
{
    handler: F,
}

impl<F, Fut> DefaultHandler<F, Fut>
where
    F: Fn(&Context) -> Fut + Send + Sync,
    Fut: std::future::Future<Output = Result<Output>> + Send,
{
    pub fn new(handler: F) -> Self {
        Self { handler }
    }
}

#[async_trait]
impl<F, Fut> CommandHandler for DefaultHandler<F, Fut>
where
    F: Fn(&Context) -> Fut + Send + Sync + 'static,
    Fut: std::future::Future<Output = Result<Output>> + Send,
{
    async fn handle(&self, ctx: &Context) -> Result<Output> {
        (self.handler)(ctx).await
    }
}

/// Command executor that coordinates command execution
pub struct CommandExecutor {
    commands: Vec<Command>,
}

impl CommandExecutor {
    pub fn new() -> Self {
        Self {
            commands: Vec::new(),
        }
    }

    pub fn register(mut self, command: Command) -> Self {
        self.commands.push(command);
        self
    }

    pub fn get_command(&self, name: &str) -> Option<&Command> {
        self.commands.iter().find(|c| c.name == name)
    }

    pub fn list_commands(&self) -> Vec<&Command> {
        self.commands.iter().collect()
    }

    pub fn registry(&self) -> CommandRegistry {
        let mut registry = CommandRegistry::new();
        for command in &self.commands {
            let _ = registry.register(command.clone());
        }
        registry
    }

    pub fn help_overview(&self) -> String {
        self.registry().help_overview()
    }

    pub fn help_for(&self, name: &str) -> Option<String> {
        self.registry().help_for(name)
    }
}

impl Default for CommandExecutor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_handler_creation() {
        let _handler =
            DefaultHandler::new(
                |_ctx: &Context| async move { Ok(Output::text("test".to_string())) },
            );
    }

    #[test]
    fn command_executor_renders_help() {
        let executor =
            CommandExecutor::new().register(Command::new("serve").description("Run the server"));

        assert!(executor.help_overview().contains("serve"));
        assert!(executor
            .help_for("serve")
            .unwrap()
            .contains("Command: serve"));
    }
}
