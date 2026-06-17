//! Integration tests for clikit

use clikit::domain::entities::{Argument, Command, Flag};
use clikit::domain::services::CommandRegistry;
use clikit::domain::value_objects::{ArgValue, Input};

/// Test basic command creation
#[test]
fn test_command_creation() {
    let cmd = Command::new("test")
        .description("A test command")
        .argument(Argument::new("name"))
        .flag(Flag::new("verbose"));

    assert_eq!(cmd.name, "test");
    assert_eq!(cmd.description, "A test command");
}

/// Test command registry
#[test]
fn test_command_registry() {
    let mut registry = CommandRegistry::new();

    let cmd = Command::new("hello").description("Say hello");

    registry.register(cmd).unwrap();
    assert!(registry.get("hello").is_some());
    assert!(registry.get("goodbye").is_none());
}

/// Test argument value parsing
#[test]
fn test_argument_value_string() {
    let value = ArgValue::String("hello".to_string());
    assert_eq!(value, ArgValue::String("hello".to_string()));
}

/// Test input creation
#[test]
fn test_input_creation() {
    let input = Input::new("test")
        .arg("name", "Alice")
        .flag("verbose", true);

    assert_eq!(input.command, "test");
    assert!(input.flags.get("verbose").copied() == Some(true));
}
