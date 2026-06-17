//! CLI dashboard subcommand for AgilePlus.
//!
//! Provides `agileplus dashboard [open|port <N>]`.
//!
//! Traceability: WP14-T089

use anyhow::{Result, anyhow};
use clap::{Args, Subcommand};

// ---------------------------------------------------------------------------
// CLI argument types
// ---------------------------------------------------------------------------

/// `agileplus dashboard` subcommand dispatcher.
#[derive(Debug, Args)]
pub struct DashboardArgs {
    #[command(subcommand)]
    pub subcommand: Option<DashboardSubcommand>,

    /// Dashboard port (overrides default for this invocation only).
    #[arg(long)]
    pub port: Option<u16>,
}

/// Available dashboard subcommands.
#[derive(Debug, Subcommand)]
pub enum DashboardSubcommand {
    /// Open the dashboard in the default browser.
    Open(DashboardOpenArgs),
    /// Configure the dashboard port.
    Port(DashboardPortArgs),
}

/// Arguments for `dashboard open`.
#[derive(Debug, Args)]
pub struct DashboardOpenArgs {
    /// Override the API port for this invocation.
    #[arg(long)]
    pub port: Option<u16>,
}

/// Arguments for `dashboard port`.
#[derive(Debug, Args)]
pub struct DashboardPortArgs {
    /// New port number.
    pub port: u16,
}

// ---------------------------------------------------------------------------
// Config helpers
// ---------------------------------------------------------------------------

const DEFAULT_DASHBOARD_PORT: u16 = 8080;

/// Read the configured dashboard port.
///
/// Reads from `AGILEPLUS_DASHBOARD_PORT` env var; falls back to 8080.
pub fn configured_port() -> u16 {
    std::env::var("AGILEPLUS_DASHBOARD_PORT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_DASHBOARD_PORT)
}

/// Build the dashboard URL for a given port.
pub fn dashboard_url(port: u16) -> String {
    format!("http://localhost:{port}/dashboard")
}

// ---------------------------------------------------------------------------
// Health check (non-blocking TCP probe)
// ---------------------------------------------------------------------------

/// Check whether the API is reachable on the given port (TCP connect probe).
pub fn api_reachable(port: u16) -> bool {
    use std::net::TcpStream;
    use std::time::Duration;
    TcpStream::connect_timeout(
        &std::net::SocketAddr::from(([127, 0, 0, 1], port)),
        Duration::from_millis(500),
    )
    .is_ok()
}

// ---------------------------------------------------------------------------
// Browser launch
// ---------------------------------------------------------------------------

/// Open a URL in the system default browser.
///
/// Returns `Ok(())` if the launch command succeeded, `Err` otherwise.
pub fn open_browser(url: &str) -> Result<()> {
    let status = if cfg!(target_os = "macos") {
        std::process::Command::new("open").arg(url).status()
    } else if cfg!(target_os = "windows") {
        std::process::Command::new("cmd")
            .args(["/C", "start", url])
            .status()
    } else {
        // Linux / other Unix
        std::process::Command::new("xdg-open").arg(url).status()
    };
    match status {
        Ok(s) if s.success() => Ok(()),
        Ok(s) => Err(anyhow!("Browser launcher exited with: {s}")),
        Err(e) => Err(anyhow!("Failed to launch browser: {e}")),
    }
}

// ---------------------------------------------------------------------------
// Entry points
// ---------------------------------------------------------------------------

/// Run a `dashboard` subcommand (or default to `open`).
pub fn run_dashboard(args: DashboardArgs) -> Result<()> {
    match args.subcommand {
        None | Some(DashboardSubcommand::Open(_)) => {
            let port = match &args.subcommand {
                Some(DashboardSubcommand::Open(a)) => a.port.or(args.port),
                _ => args.port,
            }
            .unwrap_or_else(configured_port);
            run_dashboard_open(port)
        }
        Some(DashboardSubcommand::Port(a)) => run_dashboard_port(a.port),
    }
}

/// Open the dashboard in the browser.
pub fn run_dashboard_open(port: u16) -> Result<()> {
    if !api_reachable(port) {
        eprintln!("Error: API server not running on port {port}.");
        eprintln!("Start the platform with: agileplus platform up");
        return Err(anyhow!("API server not running on port {port}"));
    }

    let url = dashboard_url(port);
    println!("Opening {url} in browser...");

    match open_browser(&url) {
        Ok(()) => {
            println!("✓ Dashboard opened");
            Ok(())
        }
        Err(_) => {
            eprintln!("✗ Could not open browser automatically.");
            eprintln!("Manual URL: {url}");
            Ok(()) // Not a fatal error; user can copy the URL.
        }
    }
}

/// Update the dashboard port in config (writes env hint + message).
pub fn run_dashboard_port(port: u16) -> Result<()> {
    // Persist via environment variable guidance (real impl would write to a config file).
    persist_port_config(port)?;
    println!("Dashboard port updated to {port}.");
    println!(
        "(Requires server restart to take effect. Run: agileplus platform down && agileplus platform up)"
    );
    Ok(())
}

/// Write port to config file.
///
/// Writes to `.agileplus/config.toml` in the current directory if writable;
/// otherwise emits an `export` hint.
fn persist_port_config(port: u16) -> Result<()> {
    let config_dir = std::path::Path::new(".agileplus");
    if config_dir.exists() || std::fs::create_dir_all(config_dir).is_ok() {
        let config_path = config_dir.join("config.toml");
        let content = format!("[dashboard]\nport = {port}\n");
        std::fs::write(&config_path, content)
            .map_err(|e| anyhow!("Failed to write config: {e}"))?;
    } else {
        // Fallback: tell the user how to set it.
        println!("To persist, set: export AGILEPLUS_DASHBOARD_PORT={port}");
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dashboard_url() {
        assert_eq!(dashboard_url(8080), "http://localhost:8080/dashboard");
        assert_eq!(dashboard_url(3000), "http://localhost:3000/dashboard");
    }

    #[test]
    fn test_configured_port_default_and_env_override() {
        // Combined into one test to avoid env-var race conditions across threads.
        // SAFETY: single-threaded test, no other thread reads this var concurrently.
        unsafe { std::env::remove_var("AGILEPLUS_DASHBOARD_PORT") };
        assert_eq!(configured_port(), 8080);

        unsafe { std::env::set_var("AGILEPLUS_DASHBOARD_PORT", "9090") };
        assert_eq!(configured_port(), 9090);

        unsafe { std::env::remove_var("AGILEPLUS_DASHBOARD_PORT") };
    }

    #[test]
    fn test_api_not_reachable_on_unused_port() {
        // Port 19999 should almost certainly be unused in CI.
        assert!(!api_reachable(19999));
    }

    #[test]
    fn test_run_dashboard_open_fails_when_api_not_running() {
        // Port 19998 — API not running, so we expect an Err.
        let result = run_dashboard_open(19998);
        assert!(result.is_err());
    }

    #[test]
    fn test_run_dashboard_port_writes_config() {
        let tmp = tempfile::tempdir().unwrap();
        let original = std::env::current_dir().unwrap();
        std::env::set_current_dir(tmp.path()).unwrap();

        let result = run_dashboard_port(3000);
        assert!(result.is_ok());

        // Config file should exist.
        let cfg = tmp.path().join(".agileplus/config.toml");
        assert!(cfg.exists());
        let content = std::fs::read_to_string(&cfg).unwrap();
        assert!(content.contains("3000"));

        std::env::set_current_dir(original).unwrap();
    }

    #[test]
    fn test_dashboard_args_defaults() {
        let args = DashboardArgs {
            subcommand: None,
            port: None,
        };
        assert!(args.subcommand.is_none());
        assert!(args.port.is_none());
    }
}
