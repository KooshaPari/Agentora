//! Application services - Orchestration logic
//!
//! Services that coordinate between multiple domain objects and ports.

use crate::domain::{
    Command, CommandRegistry, ConfigLoader, Context, Input, InputValidator, Logger, Output, Result,
    Telemetry,
};

/// Main CLI application service
pub struct CliApplication {
    commands: Vec<Command>,
    config_loader: Option<Box<dyn ConfigLoader>>,
    logger: Option<Box<dyn Logger>>,
    telemetry: Option<Box<dyn Telemetry>>,
}

impl CliApplication {
    pub fn new() -> Self {
        Self {
            commands: Vec::new(),
            config_loader: None,
            logger: None,
            telemetry: None,
        }
    }

    pub fn command(mut self, command: Command) -> Self {
        self.commands.push(command);
        self
    }

    pub fn with_config_loader(mut self, loader: Box<dyn ConfigLoader>) -> Self {
        self.config_loader = Some(loader);
        self
    }

    pub fn with_logger(mut self, logger: Box<dyn Logger>) -> Self {
        self.logger = Some(logger);
        self
    }

    pub fn with_telemetry(mut self, telemetry: Box<dyn Telemetry>) -> Self {
        self.telemetry = Some(telemetry);
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

    pub fn help(&self) -> String {
        self.registry().help_overview()
    }

    pub fn help_for(&self, name: &str) -> Option<String> {
        self.registry().help_for(name)
    }

    pub fn context(&self, input: Input) -> Context {
        let mut context = Context::new(input);

        if let Some(ref loader) = self.config_loader {
            if let Ok(config) = loader.load() {
                if let Some(map) = config.as_object() {
                    context.config = map.clone().into_iter().collect();
                }
            }
        }

        context
    }

    pub fn config_value(&self, key: &str) -> Option<serde_json::Value> {
        self.config_loader
            .as_ref()
            .and_then(|loader| loader.get(key).ok().flatten())
    }

    pub fn run(&self, input: Input) -> Result<Output> {
        let start = std::time::Instant::now();
        let cmd_name = input.command.clone();
        let context = self.context(input);

        if let Some(ref logger) = self.logger {
            logger.info(&format!("Executing command: {}", cmd_name));
            if !context.config.is_empty() {
                logger.debug(&format!("Loaded {} config entries", context.config.len()));
            }
        }

        let result = self.execute_internal(&cmd_name, context.input);

        let duration = start.elapsed().as_millis() as u64;

        if let Some(ref telemetry) = self.telemetry {
            let success = result.is_ok();
            telemetry.record_execution(&cmd_name, duration, success);
        }

        result
    }

    fn execute_internal(&self, name: &str, input: Input) -> Result<Output> {
        let command = self
            .get_command(name)
            .ok_or_else(|| crate::domain::DomainError::CommandNotFound(name.to_string()))?;

        let validator = InputValidator::new(self.commands.clone());
        validator.validate(&input)?;

        Ok(Output::text(CommandRegistry::format_command_help(command)))
    }
}

impl Default for CliApplication {
    fn default() -> Self {
        Self::new()
    }
}

impl CliApplication {
    /// Create from a single command
    pub fn from_command(command: Command) -> Self {
        Self::new().command(command)
    }
}
