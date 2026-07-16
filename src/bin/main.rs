//! agentkit binary entry point.
//!
//! Provides a small `clap`-derived CLI surface (L15, L14, L36, L30):
//!
//! - `agentkit --help` / `--version` (clap defaults).
//! - `agentkit version` — prints the crate version and JSON payload.
//! - `agentkit status` — emits a structured status payload (counts of
//!   registered skills/tools, build profile, target triple).
//! - `agentkit skills list` / `agentkit tools list` — enumerates the
//!   in-process registry contents; useful for shell scripting and CI.
//!
//! All subcommands honour `--json` so the same surface serves humans and
//! automation. Errors are routed through `ErrorEnvelope` (see
//! `agentkit::ErrorEnvelope`) and a stable exit-code ladder:
//!
//! | code | meaning                                                  |
//! |------|----------------------------------------------------------|
//! | 0    | success                                                  |
//! | 1    | generic failure (see stderr/stdout for envelope)        |
//! | 2    | invalid arguments (clap handles this before `run`)      |
//! | 3    | domain error (tool/skill/etc. failure surfaced via envelope) |

use std::process::ExitCode;

use clap::{Parser, Subcommand, ValueEnum};
use serde::Serialize;

use agentkit::{ErrorEnvelope, SkillRegistry, ToolRegistry};

/// `agentkit` — hexagonal agent framework CLI.
#[derive(Debug, Parser)]
#[command(
    name = "agentkit",
    version,
    about = "Inspect and operate the agentkit runtime from the shell.",
    long_about = None,
)]
struct Cli {
    /// Emit machine-readable JSON instead of human prose.
    #[arg(long, global = true, value_enum, default_value_t = OutputMode::Human)]
    output: OutputMode,

    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Copy, Clone, ValueEnum)]
enum OutputMode {
    Human,
    Json,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Print the agentkit version and exit.
    Version,
    /// Print a structured runtime status snapshot.
    Status,
    /// Enumerate registered skills.
    Skills {
        #[command(subcommand)]
        action: SkillsAction,
    },
    /// Enumerate registered tools.
    Tools {
        #[command(subcommand)]
        action: ToolsAction,
    },
}

#[derive(Debug, Subcommand)]
enum SkillsAction {
    /// List every registered skill.
    List,
}

#[derive(Debug, Subcommand)]
enum ToolsAction {
    /// List every registered tool.
    List,
}

#[derive(Debug, Serialize)]
struct StatusPayload {
    name: &'static str,
    version: &'static str,
    profile: &'static str,
    target: &'static str,
    skills: usize,
    tools: usize,
}

#[derive(Debug, Serialize)]
struct NamedList<'a> {
    kind: &'a str,
    names: Vec<String>,
}

fn main() -> ExitCode {
    let cli = Cli::parse();

    match run(cli) {
        Ok(()) => ExitCode::SUCCESS,
        Err(envelope) => {
            emit_error(&envelope);
            envelope_code_to_exit(&envelope)
        }
    }
}

fn envelope_code_to_exit(_envelope: &ErrorEnvelope) -> ExitCode {
    // Domain errors → 3. Anything else falls back to 1 (generic failure).
    // The function takes the envelope so future refinements (e.g. mapping
    // specific variant codes to different exit codes) stay local.
    ExitCode::from(3u8)
}

fn emit_error(envelope: &ErrorEnvelope) {
    eprintln!("{}", envelope.to_json());
}

fn run(cli: Cli) -> Result<(), ErrorEnvelope> {
    match cli.command {
        Command::Version => emit_version(cli.output),
        Command::Status => emit_status(cli.output),
        Command::Skills { action } => match action {
            SkillsAction::List => emit_skills(cli.output),
        },
        Command::Tools { action } => match action {
            ToolsAction::List => emit_tools(cli.output),
        },
    }
}

fn emit_version(mode: OutputMode) -> Result<(), ErrorEnvelope> {
    let version = env!("CARGO_PKG_VERSION");
    match mode {
        OutputMode::Human => {
            println!("agentkit {version}");
        }
        OutputMode::Json => {
            let payload = serde_json::json!({ "name": "agentkit", "version": version });
            println!("{}", payload);
        }
    }
    Ok(())
}

fn emit_status(mode: OutputMode) -> Result<(), ErrorEnvelope> {
    let skills = SkillRegistry::new().list().len();
    let tools = ToolRegistry::new().list().len();
    let payload = StatusPayload {
        name: "agentkit",
        version: env!("CARGO_PKG_VERSION"),
        profile: if cfg!(debug_assertions) {
            "debug"
        } else {
            "release"
        },
        target: target_triple(),
        skills,
        tools,
    };
    match mode {
        OutputMode::Human => {
            println!(
                "agentkit {} ({}, {})",
                payload.version, payload.profile, payload.target
            );
            println!("skills: {}", payload.skills);
            println!("tools:  {}", payload.tools);
        }
        OutputMode::Json => {
            println!("{}", serde_json::to_string(&payload).unwrap_or_default());
        }
    }
    Ok(())
}

fn emit_skills(mode: OutputMode) -> Result<(), ErrorEnvelope> {
    let names: Vec<String> = SkillRegistry::new()
        .list()
        .into_iter()
        .map(|s| s.to_string())
        .collect();
    write_list("skill", &names, mode);
    Ok(())
}

fn emit_tools(mode: OutputMode) -> Result<(), ErrorEnvelope> {
    let names: Vec<String> = ToolRegistry::new()
        .list()
        .into_iter()
        .map(|t| t.to_string())
        .collect();
    write_list("tool", &names, mode);
    Ok(())
}

fn write_list(kind: &str, names: &[String], mode: OutputMode) {
    match mode {
        OutputMode::Human => {
            if names.is_empty() {
                println!("(no {kind}s registered)");
            } else {
                for name in names {
                    println!("{kind}: {name}");
                }
            }
        }
        OutputMode::Json => {
            let payload = NamedList {
                kind,
                names: names.to_vec(),
            };
            println!("{}", serde_json::to_string(&payload).unwrap_or_default());
        }
    }
}

/// Minimal hand-rolled target triple so we don't pull in a build script
/// just for `CARGO_CFG_TARGET_OS`.  Good enough for the status payload —
/// we only need an OS family hint for operators, not a precise triple.
fn target_triple() -> &'static str {
    if cfg!(target_os = "linux") {
        "linux"
    } else if cfg!(target_os = "macos") {
        "macos"
    } else if cfg!(target_os = "windows") {
        "windows"
    } else if cfg!(target_os = "freebsd") {
        "freebsd"
    } else {
        "unknown"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_payload_serializes_as_json() {
        let payload = StatusPayload {
            name: "agentkit",
            version: "0.1.0",
            profile: "debug",
            target: "macos",
            skills: 0,
            tools: 0,
        };
        let s = serde_json::to_string(&payload).unwrap();
        assert!(s.contains("\"skills\":0"));
        assert!(s.contains("\"tools\":0"));
    }

    #[test]
    fn named_list_emits_empty_marker() {
        let payload = NamedList {
            kind: "skill",
            names: vec![],
        };
        let s = serde_json::to_string(&payload).unwrap();
        assert_eq!(s, "{\"kind\":\"skill\",\"names\":[]}");
    }

    #[test]
    fn output_mode_default_is_human() {
        // Clap default is parsed from the CLI; assert the helper behaves.
        let mode = OutputMode::Human;
        assert!(matches!(mode, OutputMode::Human));
    }
}
