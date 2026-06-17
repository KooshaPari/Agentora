//! CLI adapter for clikit
//!
//! This adapter provides a small, testable parser/dispatcher bridge
//! for the first migration slice from `phenotype-cli-core`.

use crate::application::services::CliApplication;
use crate::domain::entities::{Argument, Command};
use crate::domain::services::CommandRegistry;
use crate::domain::value_objects::{Input, Output, OutputContent, ParsedInput};
use crate::domain::{CliParser, Result};
use clap::Parser;

#[derive(Parser, Debug, Clone)]
#[command(name = "clikit-example", version, about = "clikit CLI adapter")]
pub struct Cli {
    #[arg(long)]
    pub config: Option<String>,

    #[arg(long)]
    pub command: Option<String>,
}

pub fn parse_cli_from_args(args: &[&str]) -> ParsedInput {
    let cli = Cli::parse_from(args);
    let command = cli.command.unwrap_or_else(|| "clikit-example".to_string());

    let mut input = ParsedInput::new(command);
    if let Some(config) = cli.config {
        input = input.arguments(std::collections::HashMap::from([(
            "config".to_string(),
            vec![config],
        )]));
    }

    input
}

pub fn to_input(parsed: ParsedInput) -> Input {
    let mut input = Input::new(parsed.command);

    if let Some(subcommand) = parsed.subcommand {
        input = input.subcommand(subcommand);
    }

    for (name, values) in parsed.arguments {
        if let Some(first) = values.into_iter().next() {
            input = input.arg(name, first);
        }
    }

    for (name, value) in parsed.options {
        input = input.opt(name, value);
    }

    for (name, value) in parsed.flags {
        input = input.flag(name, value);
    }

    input
}

pub fn default_app() -> CliApplication {
    CliApplication::from_command(
        Command::new("clikit-example")
            .description("Default clikit migration slice")
            .argument(Argument::new("config").description("Config file path")),
    )
}

pub struct PrimaryCliParser;

impl PrimaryCliParser {
    pub fn new() -> Self {
        Self
    }

    pub fn registry_help(registry: &CommandRegistry) -> String {
        registry.help_overview()
    }

    pub fn command_help(command: &Command) -> String {
        CommandRegistry::format_command_help(command)
    }
}

impl Default for PrimaryCliParser {
    fn default() -> Self {
        Self::new()
    }
}

impl CliParser for PrimaryCliParser {
    fn parse(&self, args: Vec<String>) -> Result<Input> {
        let refs: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        Ok(to_input(parse_cli_from_args(&refs)))
    }

    fn format_help(&self, command: &Command) -> String {
        Self::command_help(command)
    }
}

pub fn run_cli() -> String {
    let parsed = parse_cli_from_args(&["clikit-example"]);
    let input = to_input(parsed);
    let app = default_app();
    let output = futures::executor::block_on(async { app.run(input) })
        .unwrap_or_else(|err| Output::error(err.to_string()));

    match output.content {
        OutputContent::Text(text)
        | OutputContent::Json(text)
        | OutputContent::Yaml(text)
        | OutputContent::Error(text) => text,
        OutputContent::None => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_config_flag_into_input() {
        let parsed = parse_cli_from_args(&["clikit-example", "--config", "settings.toml"]);
        let input = to_input(parsed);
        assert_eq!(input.command, "clikit-example");
        assert_eq!(input.get_str("config"), Some("settings.toml"));
    }

    #[test]
    fn default_app_contains_command_metadata() {
        let app = default_app();
        let command = app.get_command("clikit-example").expect("command exists");
        assert_eq!(command.name, "clikit-example");
    }

    #[test]
    fn primary_cli_parser_formats_help() {
        let parser = PrimaryCliParser::new();
        let command = Command::new("serve")
            .description("Run the local server")
            .version("1.2.3")
            .argument(
                Argument::new("config")
                    .description("Config file path")
                    .required(),
            )
            .flag(
                crate::domain::entities::Flag::new("verbose")
                    .short('v')
                    .description("Verbose output"),
            );

        let help = parser.format_help(&command);
        assert!(help.contains("Command: serve"));
        assert!(help.contains("Description: Run the local server"));
        assert!(help.contains("Arguments:"));
        assert!(help.contains("Flags:"));
    }

    #[test]
    fn primary_cli_parser_parses_args() {
        let parser = PrimaryCliParser::new();
        let input = parser
            .parse(vec![
                "clikit-example".to_string(),
                "--config".to_string(),
                "settings.toml".to_string(),
            ])
            .expect("parse succeeds");

        assert_eq!(input.command, "clikit-example");
        assert_eq!(input.get_str("config"), Some("settings.toml"));
    }
}
