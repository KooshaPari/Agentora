use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Sync direction for a report entry.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SyncDirection {
    Push,
    Pull,
}

/// Outcome of a single sync item.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SyncItemOutcome {
    Created,
    Updated,
    Skipped,
    Conflict,
    Imported,
}

/// A single entry in a sync report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncReportEntry {
    pub entity_name: String,
    pub entity_kind: String,
    pub outcome: SyncItemOutcome,
    pub plane_id: Option<String>,
    pub message: Option<String>,
}

/// Summary report returned after a push or pull operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncReport {
    pub direction: SyncDirection,
    pub entries: Vec<SyncReportEntry>,
    pub duration_ms: u64,
}

impl SyncReport {
    pub fn new(direction: SyncDirection) -> Self {
        Self {
            direction,
            entries: Vec::new(),
            duration_ms: 0,
        }
    }

    pub fn add(&mut self, entry: SyncReportEntry) {
        self.entries.push(entry);
    }
}

/// Per-entity sync status row for `sync status`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncStatusRow {
    pub entity_kind: String,
    pub entity_name: String,
    pub local_state: String,
    pub remote_state: Option<String>,
    pub last_synced: Option<DateTime<Utc>>,
    pub in_sync: bool,
    pub conflict_count: u32,
}

/// Conflict record for `sync resolve`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConflict {
    pub entity_kind: String,
    pub entity_id: String,
    pub entity_name: String,
    pub local_state: String,
    pub local_description: String,
    pub remote_state: String,
    pub remote_description: String,
}

/// Resolution choice from the user.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConflictResolution {
    KeepLocal,
    AcceptRemote,
    MergeManually,
    Cancel,
}
