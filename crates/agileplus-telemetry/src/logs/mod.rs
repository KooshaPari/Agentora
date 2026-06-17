//! Structured JSON logging via the `tracing` crate.
//!
//! Call [`init_logging`] exactly once from `main()` and hold the returned
//! [`WorkerGuard`] for the process lifetime.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing_appender::non_blocking::WorkerGuard;
use tracing_subscriber::{EnvFilter, fmt::format::FmtSpan, prelude::*};

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// Where structured logs are written.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
#[derive(Default)]
pub enum LogOutput {
    #[default]
    Stdout,
    File(PathBuf),
    Both(PathBuf),
}

/// Configuration for structured JSON logging.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogConfig {
    /// Minimum log level (`trace`, `debug`, `info`, `warn`, `error`).
    #[serde(default = "default_level")]
    pub level: String,
    /// Output destination.
    #[serde(default)]
    pub output: LogOutput,
    /// Include parent span IDs in log lines.
    #[serde(default = "default_true")]
    pub include_spans: bool,
    /// Include module path in log lines.
    #[serde(default = "default_true")]
    pub include_target: bool,
}

fn default_level() -> String {
    "info".into()
}
fn default_true() -> bool {
    true
}

impl Default for LogConfig {
    fn default() -> Self {
        Self {
            level: default_level(),
            output: LogOutput::Stdout,
            include_spans: true,
            include_target: true,
        }
    }
}

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum LogError {
    #[error("failed to open log file {path}: {source}")]
    FileOpen {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("subscriber initialisation failed: {0}")]
    Init(String),
}

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

/// Initialise the global `tracing` subscriber.
///
/// Must be called exactly once (idempotent via `try_init`).  Returns a
/// [`WorkerGuard`] that must be held for the process lifetime.
pub fn init_logging(config: &LogConfig) -> Result<WorkerGuard, LogError> {
    let filter = build_filter(config);

    match &config.output {
        LogOutput::Stdout => {
            let (writer, guard) = tracing_appender::non_blocking(std::io::stdout());
            let layer = tracing_subscriber::fmt::layer()
                .json()
                .with_writer(writer)
                .with_target(config.include_target)
                .with_span_list(config.include_spans)
                .with_span_events(FmtSpan::CLOSE)
                .with_current_span(true);

            tracing_subscriber::registry()
                .with(filter)
                .with(layer)
                .try_init()
                .map_err(|e| LogError::Init(e.to_string()))?;

            Ok(guard)
        }
        LogOutput::File(path) => {
            let dir = path.parent().unwrap_or(std::path::Path::new("."));
            let file_name = path
                .file_name()
                .unwrap_or_else(|| std::ffi::OsStr::new("agileplus.log"));
            let appender = tracing_appender::rolling::daily(dir, file_name);
            let (writer, guard) = tracing_appender::non_blocking(appender);
            let layer = tracing_subscriber::fmt::layer()
                .json()
                .with_writer(writer)
                .with_target(config.include_target)
                .with_span_list(config.include_spans)
                .with_span_events(FmtSpan::CLOSE)
                .with_current_span(true);

            tracing_subscriber::registry()
                .with(filter)
                .with(layer)
                .try_init()
                .map_err(|e| LogError::Init(e.to_string()))?;

            Ok(guard)
        }
        LogOutput::Both(path) => {
            let (stdout_writer, guard) = tracing_appender::non_blocking(std::io::stdout());
            let stdout_layer = tracing_subscriber::fmt::layer()
                .json()
                .with_writer(stdout_writer)
                .with_target(config.include_target)
                .with_span_list(config.include_spans)
                .with_span_events(FmtSpan::CLOSE)
                .with_current_span(true);

            let dir = path.parent().unwrap_or(std::path::Path::new("."));
            let file_name = path
                .file_name()
                .unwrap_or_else(|| std::ffi::OsStr::new("agileplus.log"));
            let appender = tracing_appender::rolling::daily(dir, file_name);
            let (file_writer, file_guard) = tracing_appender::non_blocking(appender);
            std::mem::forget(file_guard);
            let file_layer = tracing_subscriber::fmt::layer()
                .json()
                .with_writer(file_writer)
                .with_target(config.include_target)
                .with_span_list(config.include_spans)
                .with_span_events(FmtSpan::CLOSE)
                .with_current_span(true);

            tracing_subscriber::registry()
                .with(filter)
                .with(stdout_layer)
                .with(file_layer)
                .try_init()
                .map_err(|e| LogError::Init(e.to_string()))?;

            Ok(guard)
        }
    }
}

fn build_filter(config: &LogConfig) -> EnvFilter {
    EnvFilter::try_from_env("AGILEPLUS_LOG")
        .or_else(|_| EnvFilter::try_from_env("RUST_LOG"))
        .unwrap_or_else(|_| {
            EnvFilter::try_new(&config.level).unwrap_or_else(|_| EnvFilter::new("info"))
        })
}

/// Explicit flush hint (actual flush happens on guard drop).
pub fn flush() {}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn log_config_defaults() {
        let cfg = LogConfig::default();
        assert_eq!(cfg.level, "info");
        assert_eq!(cfg.output, LogOutput::Stdout);
        assert!(cfg.include_spans);
        assert!(cfg.include_target);
    }

    #[test]
    fn log_config_serde_roundtrip() {
        let yaml = r#"
level: "debug"
output: "stdout"
include_spans: false
include_target: true
"#;
        let cfg: LogConfig = serde_yaml::from_str(yaml).unwrap();
        assert_eq!(cfg.level, "debug");
        assert!(!cfg.include_spans);
    }
}
