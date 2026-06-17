use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

/// Auto-sync config persisted to `.agileplus/sync-config.json`.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SyncConfig {
    pub auto_sync_enabled: bool,
}

impl SyncConfig {
    /// Load from `<root>/.agileplus/sync-config.json`, returning default if absent.
    pub fn load(project_root: &Path) -> Result<Self> {
        let path = config_path(project_root);
        if !path.exists() {
            return Ok(Self::default());
        }
        let raw = std::fs::read_to_string(&path)
            .with_context(|| format!("reading {}", path.display()))?;
        serde_json::from_str(&raw).context("parsing sync-config.json")
    }

    /// Persist to `<root>/.agileplus/sync-config.json`.
    pub fn save(&self, project_root: &Path) -> Result<()> {
        let path = config_path(project_root);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(self)?;
        std::fs::write(&path, json).with_context(|| format!("writing {}", path.display()))
    }
}

fn config_path(root: &Path) -> PathBuf {
    root.join(".agileplus").join("sync-config.json")
}
