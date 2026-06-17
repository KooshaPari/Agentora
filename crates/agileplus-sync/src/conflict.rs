//! Conflict detection for sync operations.
//!
//! Traceability: FR-SYNC-CONFLICT / WP09-T054

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Represents a detected synchronization conflict between local and remote versions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConflict {
    /// Type of entity (e.g., "feature", "work_package").
    pub entity_type: String,
    /// Local identifier of the entity.
    pub entity_id: i64,
    /// Local version of the entity as a JSON value.
    pub local_version: serde_json::Value,
    /// Remote version of the entity as a JSON value.
    pub remote_version: serde_json::Value,
    /// SHA-256 hash of the local version.
    pub local_hash: String,
    /// SHA-256 hash of the remote version.
    pub remote_hash: String,
    /// Timestamp when the conflict was detected.
    pub detected_at: DateTime<Utc>,
}

impl SyncConflict {
    /// Create a new conflict from local and remote JSON values.
    pub fn new(
        entity_type: impl Into<String>,
        entity_id: i64,
        local_version: serde_json::Value,
        remote_version: serde_json::Value,
    ) -> Self {
        let local_hash = hash_value(&local_version);
        let remote_hash = hash_value(&remote_version);
        Self {
            entity_type: entity_type.into(),
            entity_id,
            local_version,
            remote_version,
            local_hash,
            remote_hash,
            detected_at: Utc::now(),
        }
    }

    /// Returns true when both versions actually differ (i.e., hashes differ).
    pub fn is_real_conflict(&self) -> bool {
        self.local_hash != self.remote_hash
    }
}

/// Compute a deterministic SHA-256 hex digest for a JSON value.
///
/// Serialises the value canonically (sorted keys via serde_json) and hashes
/// the UTF-8 bytes.
pub fn hash_value(value: &serde_json::Value) -> String {
    let bytes = serde_json::to_vec(value).unwrap_or_default();
    let digest = Sha256::digest(&bytes);
    format!("{digest:x}")
}

/// Detect whether `local` and `remote` diverge from the stored `stored_hash`.
///
/// Returns `Some(SyncConflict)` when both hashes differ from the stored baseline
/// and from each other — meaning both sides changed independently.
pub fn detect_conflict(
    entity_type: &str,
    entity_id: i64,
    local: serde_json::Value,
    remote: serde_json::Value,
    stored_hash: &str,
) -> Option<SyncConflict> {
    let local_hash = hash_value(&local);
    let remote_hash = hash_value(&remote);

    let local_changed = local_hash != stored_hash;
    let remote_changed = remote_hash != stored_hash;

    if local_changed && remote_changed && local_hash != remote_hash {
        Some(SyncConflict {
            entity_type: entity_type.to_string(),
            entity_id,
            local_version: local,
            remote_version: remote,
            local_hash,
            remote_hash,
            detected_at: Utc::now(),
        })
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn hash_value_is_deterministic() {
        let v = json!({"a": 1, "b": "hello"});
        assert_eq!(hash_value(&v), hash_value(&v));
    }

    #[test]
    fn hash_value_differs_for_different_values() {
        let a = json!({"x": 1});
        let b = json!({"x": 2});
        assert_ne!(hash_value(&a), hash_value(&b));
    }

    #[test]
    fn sync_conflict_new() {
        let local = json!({"title": "local"});
        let remote = json!({"title": "remote"});
        let c = SyncConflict::new("feature", 42, local.clone(), remote.clone());
        assert_eq!(c.entity_type, "feature");
        assert_eq!(c.entity_id, 42);
        assert!(c.is_real_conflict());
    }

    #[test]
    fn detect_conflict_both_changed() {
        let stored = hash_value(&json!({"title": "original"}));
        let local = json!({"title": "local change"});
        let remote = json!({"title": "remote change"});
        let result = detect_conflict("wp", 1, local, remote, &stored);
        assert!(result.is_some());
    }

    #[test]
    fn detect_conflict_only_local_changed() {
        let original = json!({"title": "original"});
        let stored = hash_value(&original);
        let local = json!({"title": "local change"});
        let remote = original.clone();
        let result = detect_conflict("wp", 1, local, remote, &stored);
        assert!(result.is_none());
    }

    #[test]
    fn detect_conflict_both_same_as_stored() {
        let original = json!({"title": "same"});
        let stored = hash_value(&original);
        let result = detect_conflict("wp", 1, original.clone(), original.clone(), &stored);
        assert!(result.is_none());
    }
}
