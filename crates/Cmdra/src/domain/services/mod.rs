//! Domain services - Domain logic
//!
//! Services that contain domain logic that doesn't belong to a single entity.

use crate::domain::{Command, DomainError, Result};
use std::fmt::Write as _;

/// Command registry service
pub struct CommandRegistry {
    commands: Vec<Command>,
}

impl CommandRegistry {
    pub fn new() -> Self {
        Self {
            commands: Vec::new(),
        }
    }

    pub fn register(&mut self, command: Command) -> Result<()> {
        if self.commands.iter().any(|c| c.name == command.name) {
            return Err(DomainError::InvalidCommand(format!(
                "Command '{}' already registered",
                command.name
            )));
        }

        self.commands.push(command);
        Ok(())
    }

    pub fn get(&self, name: &str) -> Option<&Command> {
        self.commands.iter().find(|c| c.name == name)
    }

    pub fn list(&self) -> Vec<&Command> {
        self.commands.iter().collect()
    }

    pub fn find_matching(&self, name: &str) -> Vec<&Command> {
        self.commands
            .iter()
            .filter(|c| c.name.contains(name) || c.description.contains(name))
            .collect()
    }

    pub fn help_overview(&self) -> String {
        if self.commands.is_empty() {
            return "No commands registered.".to_string();
        }

        let mut output = String::from("Available commands:\n");
        for command in &self.commands {
            let description = if command.description.is_empty() {
                "(no description)"
            } else {
                &command.description
            };
            let _ = writeln!(output, "  {} - {}", command.name, description);
        }

        output.trim_end().to_string()
    }

    pub fn help_for(&self, name: &str) -> Option<String> {
        self.get(name).map(Self::format_command_help)
    }

    pub fn format_command_help(command: &Command) -> String {
        let mut output = String::new();
        let _ = writeln!(output, "Command: {}", command.name);

        if !command.description.is_empty() {
            let _ = writeln!(output, "Description: {}", command.description);
        }

        if let Some(version) = &command.version {
            let _ = writeln!(output, "Version: {}", version);
        }

        if !command.arguments.is_empty() {
            let _ = writeln!(output, "Arguments:");
            for arg in &command.arguments {
                let requirement = if arg.required { "required" } else { "optional" };
                let description = if arg.description.is_empty() {
                    "(no description)"
                } else {
                    &arg.description
                };
                let default_value = arg
                    .default_value
                    .as_deref()
                    .map(|value| format!(" (default: {})", value))
                    .unwrap_or_default();
                let _ = writeln!(
                    output,
                    "  {} [{}] - {}{}",
                    arg.name, requirement, description, default_value
                );
            }
        }

        if !command.options.is_empty() {
            let _ = writeln!(output, "Options:");
            for opt in &command.options {
                let short = opt.short.map(|c| format!("-{}, ", c)).unwrap_or_default();
                let description = if opt.description.is_empty() {
                    "(no description)"
                } else {
                    &opt.description
                };
                let value_name = if opt.value_name.is_empty() {
                    String::new()
                } else {
                    format!(" <{}>", opt.value_name)
                };
                let default_value = opt
                    .default_value
                    .as_deref()
                    .map(|value| format!(" (default: {})", value))
                    .unwrap_or_default();
                let requirement = if opt.required { "required" } else { "optional" };
                let _ = writeln!(
                    output,
                    "  {}--{}{} [{}] - {}{}",
                    short, opt.long, value_name, requirement, description, default_value
                );
            }
        }

        if !command.flags.is_empty() {
            let _ = writeln!(output, "Flags:");
            for flag in &command.flags {
                let short = flag.short.map(|c| format!("-{}, ", c)).unwrap_or_default();
                let description = if flag.description.is_empty() {
                    "(no description)"
                } else {
                    &flag.description
                };
                let _ = writeln!(output, "  {}--{} - {}", short, flag.long, description);
            }
        }

        output.trim_end().to_string()
    }
}

impl Default for CommandRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Input validation service
pub struct InputValidator {
    commands: Vec<Command>,
}

impl InputValidator {
    pub fn new(commands: Vec<Command>) -> Self {
        Self { commands }
    }

    pub fn validate(&self, input: &crate::domain::Input) -> Result<()> {
        let command = self
            .commands
            .iter()
            .find(|c| c.name == input.command)
            .ok_or_else(|| DomainError::CommandNotFound(input.command.clone()))?;

        for arg in &command.arguments {
            if arg.required && !input.args.contains_key(&arg.name) {
                return Err(DomainError::MissingArgument(arg.name.clone()));
            }
        }

        Ok(())
    }
}
