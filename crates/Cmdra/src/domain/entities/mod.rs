//! Domain entities - Core business objects
//!
//! Entities are the core objects of the domain that have identity.
//! They encapsulate state and behavior.

use std::collections::HashMap;

/// Command represents a CLI command with its metadata
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Command {
    /// Unique name of the command
    pub name: String,
    /// Human-readable description
    pub description: String,
    /// Version string
    pub version: Option<String>,
    /// Subcommands
    pub subcommands: Vec<Command>,
    /// Arguments
    pub arguments: Vec<Argument>,
    /// Options (flags)
    pub options: Vec<CliOption>,
    /// Flags
    pub flags: Vec<Flag>,
}

impl Command {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            description: String::new(),
            version: None,
            subcommands: Vec::new(),
            arguments: Vec::new(),
            options: Vec::new(),
            flags: Vec::new(),
        }
    }

    pub fn description(mut self, desc: impl Into<String>) -> Self {
        self.description = desc.into();
        self
    }

    pub fn version(mut self, version: impl Into<String>) -> Self {
        self.version = Some(version.into());
        self
    }

    pub fn subcommand(mut self, cmd: Command) -> Self {
        self.subcommands.push(cmd);
        self
    }

    pub fn argument(mut self, arg: Argument) -> Self {
        self.arguments.push(arg);
        self
    }

    pub fn option(mut self, opt: CliOption) -> Self {
        self.options.push(opt);
        self
    }

    pub fn flag(mut self, flag: Flag) -> Self {
        self.flags.push(flag);
        self
    }
}

/// Argument represents a positional argument
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Argument {
    pub name: String,
    pub description: String,
    pub required: bool,
    pub default_value: Option<String>,
    pub multiple: bool,
}

impl Argument {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            description: String::new(),
            required: false,
            default_value: None,
            multiple: false,
        }
    }

    pub fn description(mut self, desc: impl Into<String>) -> Self {
        self.description = desc.into();
        self
    }

    pub fn required(mut self) -> Self {
        self.required = true;
        self
    }

    pub fn default_value(mut self, value: impl Into<String>) -> Self {
        self.default_value = Some(value.into());
        self
    }

    pub fn multiple(mut self) -> Self {
        self.multiple = true;
        self
    }
}

/// CliOption represents a named option (--name value)
/// Renamed from Option to avoid collision with std::option::Option
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CliOption {
    pub short: Option<char>,
    pub long: String,
    pub description: String,
    pub value_name: String,
    pub required: bool,
    pub default_value: Option<String>,
}

impl CliOption {
    pub fn long(mut self, long: impl Into<String>) -> Self {
        self.long = long.into();
        self
    }

    pub fn short(mut self, short: char) -> Self {
        self.short = Some(short);
        self
    }

    pub fn description(mut self, desc: impl Into<String>) -> Self {
        self.description = desc.into();
        self
    }

    pub fn value_name(mut self, name: impl Into<String>) -> Self {
        self.value_name = name.into();
        self
    }

    pub fn required(mut self) -> Self {
        self.required = true;
        self
    }

    pub fn default_value(mut self, value: impl Into<String>) -> Self {
        self.default_value = Some(value.into());
        self
    }
}

/// Flag represents a boolean flag
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Flag {
    pub short: Option<char>,
    pub long: String,
    pub description: String,
}

impl Flag {
    pub fn new(long: impl Into<String>) -> Self {
        Self {
            short: None,
            long: long.into(),
            description: String::new(),
        }
    }

    pub fn short(mut self, short: char) -> Self {
        self.short = Some(short);
        self
    }

    pub fn description(mut self, desc: impl Into<String>) -> Self {
        self.description = desc.into();
        self
    }
}

/// ParsedInput represents the parsed CLI input
#[derive(Debug, Clone)]
pub struct ParsedInput {
    pub command: String,
    pub subcommand: Option<String>,
    pub arguments: HashMap<String, Vec<String>>,
    pub options: HashMap<String, Option<String>>,
    pub flags: HashMap<String, bool>,
}

impl ParsedInput {
    pub fn new(command: impl Into<String>) -> Self {
        Self {
            command: command.into(),
            subcommand: None,
            arguments: HashMap::new(),
            options: HashMap::new(),
            flags: HashMap::new(),
        }
    }

    /// Set arguments (builder pattern)
    pub fn arguments(mut self, args: HashMap<String, Vec<String>>) -> Self {
        self.arguments = args;
        self
    }

    pub fn get_arg(&self, name: &str) -> Option<&str> {
        self.arguments
            .get(name)
            .and_then(|v| v.first().map(|s| s.as_str()))
    }

    pub fn get_opt(&self, name: &str) -> Option<&str> {
        self.options.get(name).and_then(|v| v.as_deref())
    }

    pub fn get_flag(&self, name: &str) -> bool {
        self.flags.get(name).copied().unwrap_or(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_command_builder() {
        let cmd = Command::new("greet")
            .description("Greet someone")
            .version("1.0.0")
            .argument(Argument::new("name").default_value("World"));

        assert_eq!(cmd.name, "greet");
        assert_eq!(cmd.arguments.len(), 1);
    }

    #[test]
    fn test_parsed_input() {
        let mut args = HashMap::new();
        args.insert("name".to_string(), vec!["Alice".to_string()]);
        let input = ParsedInput::new("greet").arguments(args);

        assert_eq!(input.get_arg("name"), Some("Alice"));
    }
}
