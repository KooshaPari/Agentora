//! Append-only JSONL audit log for sub-command invocations.
//!
//! Each invocation records pre-dispatch and post-dispatch entries.
//!
//! Traceability: WP20-T120

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// A single audit log entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub timestamp: DateTime<Utc>,
    pub command: String,
    pub phase: AuditPhase,
    pub agent: Option<String>,
    pub feature_slug: Option<String>,
    pub args: serde_json::Value,
    pub result: Option<AuditResult>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AuditPhase {
    PreDispatch,
    PostDispatch,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditResult {
    pub success: bool,
    pub message: String,
    pub duration_ms: u64,
}

/// Append-only JSONL audit log.
#[derive(Debug)]
pub struct AuditLog {
    path: PathBuf,
}

impl AuditLog {
    /// Create or open an audit log at the given path.
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    /// Default path: `.agileplus/audit.jsonl`
    pub fn default_path(project_root: &Path) -> Self {
        Self {
            path: project_root.join(".agileplus").join("audit.jsonl"),
        }
    }

    /// Append a pre-dispatch entry.
    pub fn log_pre_dispatch(
        &self,
        command: &str,
        agent: Option<&str>,
        feature_slug: Option<&str>,
        args: serde_json::Value,
    ) -> anyhow::Result<()> {
        let entry = AuditEntry {
            timestamp: Utc::now(),
            command: command.to_string(),
            phase: AuditPhase::PreDispatch,
            agent: agent.map(|s| s.to_string()),
            feature_slug: feature_slug.map(|s| s.to_string()),
            args,
            result: None,
        };
        self.append(&entry)
    }

    /// Append a post-dispatch entry with result.
    pub fn log_post_dispatch(
        &self,
        command: &str,
        agent: Option<&str>,
        feature_slug: Option<&str>,
        success: bool,
        message: &str,
        duration_ms: u64,
    ) -> anyhow::Result<()> {
        let entry = AuditEntry {
            timestamp: Utc::now(),
            command: command.to_string(),
            phase: AuditPhase::PostDispatch,
            agent: agent.map(|s| s.to_string()),
            feature_slug: feature_slug.map(|s| s.to_string()),
            args: serde_json::Value::Null,
            result: Some(AuditResult {
                success,
                message: message.to_string(),
                duration_ms,
            }),
        };
        self.append(&entry)
    }

    /// Read all entries from the log.
    pub fn read_all(&self) -> anyhow::Result<Vec<AuditEntry>> {
        if !self.path.exists() {
            return Ok(Vec::new());
        }
        let content = fs::read_to_string(&self.path)?;
        let mut entries = Vec::new();
        for line in content.lines() {
            if line.trim().is_empty() {
                continue;
            }
            let entry: AuditEntry = serde_json::from_str(line)?;
            entries.push(entry);
        }
        Ok(entries)
    }

    fn append(&self, entry: &AuditEntry) -> anyhow::Result<()> {
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent)?;
        }
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)?;
        let json = serde_json::to_string(entry)?;
        writeln!(file, "{json}")?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn audit_log_write_and_read() {
        let tmp = TempDir::new().unwrap();
        let log = AuditLog::new(tmp.path().join("audit.jsonl"));

        log.log_pre_dispatch(
            "triage:classify",
            Some("claude"),
            Some("my-feature"),
            serde_json::json!({"input": "fix this bug"}),
        )
        .unwrap();

        log.log_post_dispatch(
            "triage:classify",
            Some("claude"),
            Some("my-feature"),
            true,
            "classified as bug",
            42,
        )
        .unwrap();

        let entries = log.read_all().unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].phase, AuditPhase::PreDispatch);
        assert_eq!(entries[1].phase, AuditPhase::PostDispatch);
        assert!(entries[1].result.as_ref().unwrap().success);
    }

    #[test]
    fn audit_log_empty() {
        let tmp = TempDir::new().unwrap();
        let log = AuditLog::new(tmp.path().join("nonexistent.jsonl"));
        let entries = log.read_all().unwrap();
        assert!(entries.is_empty());
    }

    #[test]
    fn audit_entry_serialization() {
        let entry = AuditEntry {
            timestamp: Utc::now(),
            command: "test:cmd".to_string(),
            phase: AuditPhase::PreDispatch,
            agent: Some("claude".to_string()),
            feature_slug: None,
            args: serde_json::json!({}),
            result: None,
        };
        let json = serde_json::to_string(&entry).unwrap();
        let restored: AuditEntry = serde_json::from_str(&json).unwrap();
        assert_eq!(restored.command, "test:cmd");
    }

    #[test]
    fn audit_log_append_only() {
        let tmp = TempDir::new().unwrap();
        let log = AuditLog::new(tmp.path().join("audit.jsonl"));

        for i in 0..5 {
            log.log_pre_dispatch(&format!("cmd:{i}"), None, None, serde_json::Value::Null)
                .unwrap();
        }

        let entries = log.read_all().unwrap();
        assert_eq!(entries.len(), 5);
        assert_eq!(entries[0].command, "cmd:0");
        assert_eq!(entries[4].command, "cmd:4");
    }

    #[test]
    fn default_path() {
        let log = AuditLog::default_path(Path::new("/project"));
        assert_eq!(log.path, PathBuf::from("/project/.agileplus/audit.jsonl"));
    }
}
