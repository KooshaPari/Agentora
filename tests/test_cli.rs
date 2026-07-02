//! CLI smoke tests.  We invoke the `agentkit` binary as a subprocess so
//! the entire surface (clap parsing, exit codes, JSON output) is exercised
//! end-to-end.  See audit finding L15/L30 — these tests guard against the
//! regression where `src/bin/main.rs` was reduced to a single
//! `println!`.

use std::process::Command;

fn agentkit_bin() -> Command {
    // `env!("CARGO_BIN_EXE_agentkit")` is set by Cargo when running
    // integration tests against a [[bin]] target.
    Command::new(env!("CARGO_BIN_EXE_agentkit"))
}

#[test]
fn help_lists_subcommands() {
    let output = agentkit_bin().arg("--help").output().expect("run --help");
    assert!(output.status.success(), "stderr: {}", String::from_utf8_lossy(&output.stderr));
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("version"));
    assert!(stdout.contains("status"));
    assert!(stdout.contains("skills"));
    assert!(stdout.contains("tools"));
}

#[test]
fn version_subcommand_prints_human_line() {
    let output = agentkit_bin().arg("version").output().expect("run version");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.starts_with("agentkit "));
}

#[test]
fn version_subcommand_with_json_flag_emits_object() {
    let output = agentkit_bin().args(["version", "--output", "json"]).output().expect("run version --output json");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    let value: serde_json::Value = serde_json::from_str(stdout.trim()).expect("valid JSON");
    assert_eq!(value["name"], "agentkit");
    assert!(value["version"].is_string());
}

#[test]
fn status_subcommand_returns_zero() {
    let output = agentkit_bin().arg("status").output().expect("run status");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("skills:"));
    assert!(stdout.contains("tools:"));
}

#[test]
fn skills_list_with_json_flag_emits_object() {
    let output = agentkit_bin().args(["skills", "list", "--output", "json"]).output().expect("run skills list --output json");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    let value: serde_json::Value = serde_json::from_str(stdout.trim()).expect("valid JSON");
    assert_eq!(value["kind"], "skill");
    assert!(value["names"].is_array());
}

#[test]
fn tools_list_with_json_flag_emits_object() {
    let output = agentkit_bin().args(["tools", "list", "--output", "json"]).output().expect("run tools list --output json");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    let value: serde_json::Value = serde_json::from_str(stdout.trim()).expect("valid JSON");
    assert_eq!(value["kind"], "tool");
    assert!(value["names"].is_array());
}

#[test]
fn unknown_subcommand_fails_with_clap_error() {
    let output = agentkit_bin().arg("nope").output().expect("run nope");
    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("error") || stderr.contains("unrecognized"));
}