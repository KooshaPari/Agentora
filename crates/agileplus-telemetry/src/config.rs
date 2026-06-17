//! OTLP and telemetry configuration loader.
//!
//! Reads `~/.agileplus/otel-config.yaml`. Missing file returns defaults (stdout
//! only, no OTLP export).  Environment variables override YAML values.

use std::{
    collections::HashMap,
    path::{Path, PathBuf},
};

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::logs::LogConfig;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("IO error reading telemetry config: {0}")]
    Io(#[from] std::io::Error),
    #[error("YAML parse error in telemetry config: {0}")]
    Yaml(#[from] serde_yaml::Error),
    #[error("invalid config: {0}")]
    Validation(String),
}

// ---------------------------------------------------------------------------
// Config structs
// ---------------------------------------------------------------------------

/// OTLP export protocol selection.
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum OtlpProtocol {
    #[default]
    Grpc,
    Http,
}

/// OTLP exporter configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OtlpConfig {
    /// gRPC/HTTP endpoint, e.g. `"http://localhost:4317"`.
    pub endpoint: String,
    /// Wire protocol — `grpc` (default) or `http`.
    #[serde(default)]
    pub protocol: OtlpProtocol,
    /// Additional headers (auth tokens, etc.).
    #[serde(default)]
    pub headers: HashMap<String, String>,
    /// Connection timeout in milliseconds (default: 5 000).
    #[serde(default = "default_timeout_ms")]
    pub timeout_ms: u64,
    /// Metrics export interval in milliseconds (default: 60 000).
    #[serde(default = "default_export_interval_ms")]
    pub export_interval_ms: u64,
}

fn default_timeout_ms() -> u64 {
    5_000
}
fn default_export_interval_ms() -> u64 {
    60_000
}

/// Trace sampling configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SamplingConfig {
    /// Fraction of traces to sample — 0.0 (none) to 1.0 (all).
    #[serde(default = "default_trace_ratio")]
    pub trace_ratio: f64,
}

fn default_trace_ratio() -> f64 {
    1.0
}

impl Default for SamplingConfig {
    fn default() -> Self {
        Self { trace_ratio: 1.0 }
    }
}

/// Top-level telemetry configuration.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TelemetryConfig {
    /// OTLP export — absent means no export (console only).
    pub otlp: Option<OtlpConfig>,
    /// Structured logging configuration.
    #[serde(default)]
    pub logging: LogConfig,
    /// Sampling configuration.
    #[serde(default)]
    pub sampling: SamplingConfig,
}

// ---------------------------------------------------------------------------
// Default YAML template
// ---------------------------------------------------------------------------

/// Default YAML config content, suitable for `agileplus init` to write.
pub const DEFAULT_CONFIG_YAML: &str = r#"# AgilePlus OpenTelemetry Configuration
# Remove or comment out the `otlp` section to disable OTLP export.
otlp:
  endpoint: "http://localhost:4317"
  protocol: grpc
  headers: {}
  timeout_ms: 5000
  export_interval_ms: 60000
logging:
  level: "info"
  output: "stdout"
  include_spans: true
  include_target: true
sampling:
  trace_ratio: 1.0
"#;

// ---------------------------------------------------------------------------
// Loaders
// ---------------------------------------------------------------------------

impl TelemetryConfig {
    /// Load from the canonical path `~/.agileplus/otel-config.yaml`.
    ///
    /// Returns `TelemetryConfig::default()` when the file does not exist.
    pub fn load() -> Result<Self, ConfigError> {
        let path = default_config_path();
        if !path.exists() {
            return Ok(Self::default_with_env_overrides());
        }
        Self::load_from(&path)
    }

    /// Load from an explicit path (useful for testing).
    pub fn load_from(path: &Path) -> Result<Self, ConfigError> {
        let content = std::fs::read_to_string(path)?;
        let mut cfg: TelemetryConfig = serde_yaml::from_str(&content)?;
        cfg.apply_env_overrides();
        cfg.validate()?;
        Ok(cfg)
    }

    // -----------------------------------------------------------------------
    // Internal helpers
    // -----------------------------------------------------------------------

    fn default_with_env_overrides() -> Self {
        let mut cfg = TelemetryConfig::default();
        cfg.apply_env_overrides();
        cfg
    }

    /// Apply environment variable overrides on top of YAML values.
    fn apply_env_overrides(&mut self) {
        if let Ok(level) = std::env::var("AGILEPLUS_LOG_LEVEL") {
            self.logging.level = level;
        }
        if let Ok(endpoint) = std::env::var("AGILEPLUS_OTLP_ENDPOINT") {
            match &mut self.otlp {
                Some(o) => o.endpoint = endpoint,
                None => {
                    self.otlp = Some(OtlpConfig {
                        endpoint,
                        protocol: OtlpProtocol::Grpc,
                        headers: HashMap::new(),
                        timeout_ms: default_timeout_ms(),
                        export_interval_ms: default_export_interval_ms(),
                    });
                }
            }
        }
    }

    /// Validate field invariants.
    fn validate(&self) -> Result<(), ConfigError> {
        let r = self.sampling.trace_ratio;
        if !(0.0..=1.0).contains(&r) {
            return Err(ConfigError::Validation(format!(
                "sampling.trace_ratio must be 0.0–1.0, got {r}"
            )));
        }
        if let Some(otlp) = &self.otlp {
            if otlp.timeout_ms == 0 {
                return Err(ConfigError::Validation(
                    "otlp.timeout_ms must be > 0".into(),
                ));
            }
            // Basic URL check.
            let _ = otlp.endpoint.parse::<url::Url>().map_err(|_| {
                ConfigError::Validation(format!(
                    "otlp.endpoint '{}' is not a valid URL",
                    otlp.endpoint
                ))
            })?;
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn default_config_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".agileplus")
        .join("otel-config.yaml")
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn missing_file_returns_defaults() {
        let cfg = TelemetryConfig::load_from(Path::new("/nonexistent/path/otel.yaml"));
        // Should error with Io not panic.
        assert!(cfg.is_err());
    }

    #[test]
    fn valid_yaml_parses() {
        let mut f = tempfile::NamedTempFile::new().unwrap();
        write!(f, "{}", DEFAULT_CONFIG_YAML).unwrap();
        let cfg = TelemetryConfig::load_from(f.path()).unwrap();
        assert!(cfg.otlp.is_some());
        assert_eq!(cfg.sampling.trace_ratio, 1.0);
    }

    #[test]
    fn invalid_trace_ratio_errors() {
        let yaml = r#"
sampling:
  trace_ratio: 2.5
"#;
        let mut f = tempfile::NamedTempFile::new().unwrap();
        write!(f, "{yaml}").unwrap();
        let err = TelemetryConfig::load_from(f.path()).unwrap_err();
        assert!(matches!(err, ConfigError::Validation(_)));
    }

    #[test]
    fn malformed_yaml_errors() {
        let mut f = tempfile::NamedTempFile::new().unwrap();
        write!(f, ": !! bad yaml {{{{").unwrap();
        let err = TelemetryConfig::load_from(f.path()).unwrap_err();
        assert!(matches!(err, ConfigError::Yaml(_)));
    }

    #[test]
    fn missing_otlp_defaults_to_none() {
        let yaml = r#"
logging:
  level: "debug"
"#;
        let mut f = tempfile::NamedTempFile::new().unwrap();
        write!(f, "{yaml}").unwrap();
        let cfg = TelemetryConfig::load_from(f.path()).unwrap();
        assert!(cfg.otlp.is_none());
    }
}
