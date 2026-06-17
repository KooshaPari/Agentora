//! Value objects - Immutable domain values
//!
//! Value objects are immutable objects defined by their attributes.
//! They have no identity and are compared by their values.

use std::collections::HashMap;

/// Input value object for CLI execution
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Input {
    /// Command name
    pub command: String,
    /// Subcommand if any
    pub subcommand: Option<String>,
    /// Arguments as key-value pairs
    pub args: HashMap<String, ArgValue>,
    /// Options as key-value pairs
    pub opts: HashMap<String, Option<String>>,
    /// Flags as key-value pairs
    pub flags: HashMap<String, bool>,
}

impl Input {
    pub fn new(command: impl Into<String>) -> Self {
        Self {
            command: command.into(),
            subcommand: None,
            args: HashMap::new(),
            opts: HashMap::new(),
            flags: HashMap::new(),
        }
    }

    pub fn arg(mut self, name: impl Into<String>, value: impl Into<ArgValue>) -> Self {
        self.args.insert(name.into(), value.into());
        self
    }

    pub fn opt(mut self, name: impl Into<String>, value: Option<String>) -> Self {
        self.opts.insert(name.into(), value);
        self
    }

    pub fn flag(mut self, name: impl Into<String>, value: bool) -> Self {
        self.flags.insert(name.into(), value);
        self
    }

    pub fn get_str(&self, name: &str) -> Option<&str> {
        match self.args.get(name)? {
            ArgValue::String(s) => Some(s),
            _ => None,
        }
    }

    pub fn get_flag(&self, name: &str) -> bool {
        self.flags.get(name).copied().unwrap_or(false)
    }

    pub fn get_opt(&self, name: &str) -> Option<&str> {
        self.opts.get(name).and_then(|s| s.as_deref())
    }

    pub fn get_arg(&self, name: &str) -> Option<&ArgValue> {
        self.args.get(name)
    }

    pub fn subcommand(mut self, sub: impl Into<String>) -> Self {
        self.subcommand = Some(sub.into());
        self
    }
}

/// Parsed input value object used by the CLI adapter
#[derive(Debug, Clone, PartialEq, Eq)]
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

    pub fn arguments(mut self, args: HashMap<String, Vec<String>>) -> Self {
        self.arguments = args;
        self
    }

    pub fn options(mut self, opts: HashMap<String, Option<String>>) -> Self {
        self.options = opts;
        self
    }

    pub fn flags(mut self, flags: HashMap<String, bool>) -> Self {
        self.flags = flags;
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

/// Argument value type
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ArgValue {
    /// Single string value
    String(String),
    /// Integer value
    Integer(i64),
    /// Boolean value
    Boolean(bool),
    /// Multiple values
    Multiple(Vec<String>),
}

impl<T: Into<String>> From<T> for ArgValue {
    fn from(s: T) -> Self {
        ArgValue::String(s.into())
    }
}

/// Output value object for CLI execution
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Output {
    /// Output content
    pub content: OutputContent,
    /// Exit code
    pub exit_code: u8,
    /// Whether to exit immediately
    pub should_exit: bool,
}

impl Output {
    pub fn text(content: impl Into<String>) -> Self {
        Self {
            content: OutputContent::Text(content.into()),
            exit_code: 0,
            should_exit: true,
        }
    }

    pub fn json<T: serde::Serialize>(value: &T) -> std::result::Result<Self, serde_json::Error> {
        let json = serde_json::to_string_pretty(value)?;
        Ok(Self {
            content: OutputContent::Json(json),
            exit_code: 0,
            should_exit: true,
        })
    }

    pub fn error(content: impl Into<String>) -> Self {
        Self {
            content: OutputContent::Error(content.into()),
            exit_code: 1,
            should_exit: true,
        }
    }

    pub fn exit_code(mut self, code: u8) -> Self {
        self.exit_code = code;
        self
    }

    pub fn no_exit(mut self) -> Self {
        self.should_exit = false;
        self
    }
}

/// Output content types
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum OutputContent {
    Text(String),
    Json(String),
    Yaml(String),
    Error(String),
    #[default]
    None,
}

impl Default for Output {
    fn default() -> Self {
        Self {
            content: OutputContent::None,
            exit_code: 0,
            should_exit: false,
        }
    }
}

/// Execution context passed to handlers
#[derive(Debug, Clone)]
pub struct Context {
    /// Parsed input
    pub input: Input,
    /// Working directory
    pub cwd: std::path::PathBuf,
    /// Environment variables
    pub env: HashMap<String, String>,
    /// Config values
    pub config: HashMap<String, serde_json::Value>,
}

impl Context {
    pub fn new(input: Input) -> Self {
        Self {
            input,
            cwd: std::env::current_dir().unwrap_or_default(),
            env: std::env::vars().collect(),
            config: HashMap::new(),
        }
    }

    pub fn get_flag(&self, name: &str) -> bool {
        self.input.get_flag(name)
    }

    pub fn get_opt(&self, name: &str) -> Option<&str> {
        self.input.get_opt(name)
    }

    pub fn get_arg(&self, name: &str) -> Option<&ArgValue> {
        self.input.get_arg(name)
    }

    pub fn get_str(&self, name: &str) -> Option<&str> {
        self.input.get_str(name)
    }
}

/// Result type for domain operations
pub type Result<T> = std::result::Result<T, super::errors::DomainError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parsed_input_roundtrip() {
        let input = ParsedInput::new("greet")
            .arguments(HashMap::from([(
                "name".to_string(),
                vec!["World".to_string()],
            )]))
            .flags(HashMap::from([("verbose".to_string(), true)]));

        assert_eq!(input.get_arg("name"), Some("World"));
        assert!(input.get_flag("verbose"));
    }

    #[test]
    fn test_output_builder() {
        let output = Output::text("Hello, World!").exit_code(0);

        match output.content {
            OutputContent::Text(s) => assert_eq!(s, "Hello, World!"),
            _ => panic!("Expected Text content"),
        }
    }
}
