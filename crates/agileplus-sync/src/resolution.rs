//! Conflict resolution strategies.
//!
//! Traceability: FR-SYNC-RESOLUTION / WP09-T055

use std::collections::HashMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::conflict::{SyncConflict, hash_value};
use crate::error::SyncError;

/// Specifies which side wins for a particular field in field-level resolution.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FieldSource {
    Local,
    Remote,
}

/// Strategy to apply when resolving a sync conflict.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "strategy", rename_all = "snake_case")]
pub enum ResolutionStrategy {
    /// Accept local version as the resolved value.
    LocalWins,
    /// Accept remote version as the resolved value.
    RemoteWins,
    /// Accept a user-provided merged value.
    Manual(Value),
    /// Pick each field from local or remote independently.
    FieldLevel(HashMap<String, FieldSource>),
}

/// The outcome of applying a resolution strategy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolutionResult {
    /// The resolved entity value.
    pub resolved_value: Value,
    /// SHA-256 hash of the resolved value.
    pub resolved_hash: String,
    /// Human-readable label for the strategy that was applied.
    pub strategy_label: String,
}

/// Apply a `ResolutionStrategy` to a `SyncConflict`, returning the resolved value.
///
/// For `FieldLevel`, unknown fields fall back to the remote value.
pub fn apply_resolution(
    conflict: &SyncConflict,
    strategy: &ResolutionStrategy,
) -> Result<ResolutionResult, SyncError> {
    let (resolved_value, strategy_label) = match strategy {
        ResolutionStrategy::LocalWins => (conflict.local_version.clone(), "local_wins".to_string()),
        ResolutionStrategy::RemoteWins => {
            (conflict.remote_version.clone(), "remote_wins".to_string())
        }
        ResolutionStrategy::Manual(v) => (v.clone(), "manual".to_string()),
        ResolutionStrategy::FieldLevel(field_map) => {
            let local_obj = conflict.local_version.as_object().ok_or_else(|| {
                SyncError::ResolutionFailed("local version is not an object".into())
            })?;
            let remote_obj = conflict.remote_version.as_object().ok_or_else(|| {
                SyncError::ResolutionFailed("remote version is not an object".into())
            })?;

            let mut merged = serde_json::Map::new();
            // Collect all field names from both sides.
            let all_keys: std::collections::HashSet<&String> =
                local_obj.keys().chain(remote_obj.keys()).collect();

            for key in all_keys {
                let source = field_map.get(key).unwrap_or(&FieldSource::Remote);
                let value = match source {
                    FieldSource::Local => local_obj
                        .get(key)
                        .or_else(|| remote_obj.get(key))
                        .cloned()
                        .unwrap_or(Value::Null),
                    FieldSource::Remote => remote_obj
                        .get(key)
                        .or_else(|| local_obj.get(key))
                        .cloned()
                        .unwrap_or(Value::Null),
                };
                merged.insert(key.clone(), value);
            }

            (Value::Object(merged), "field_level".to_string())
        }
    };

    let resolved_hash = hash_value(&resolved_value);
    Ok(ResolutionResult {
        resolved_value,
        resolved_hash,
        strategy_label,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::conflict::SyncConflict;
    use serde_json::json;

    fn make_conflict() -> SyncConflict {
        SyncConflict::new(
            "feature",
            1,
            json!({"title": "local title", "status": "open"}),
            json!({"title": "remote title", "status": "closed"}),
        )
    }

    #[test]
    fn local_wins() {
        let c = make_conflict();
        let result = apply_resolution(&c, &ResolutionStrategy::LocalWins).unwrap();
        assert_eq!(result.resolved_value["title"], "local title");
        assert_eq!(result.strategy_label, "local_wins");
    }

    #[test]
    fn remote_wins() {
        let c = make_conflict();
        let result = apply_resolution(&c, &ResolutionStrategy::RemoteWins).unwrap();
        assert_eq!(result.resolved_value["title"], "remote title");
        assert_eq!(result.strategy_label, "remote_wins");
    }

    #[test]
    fn manual_resolution() {
        let c = make_conflict();
        let merged = json!({"title": "manual title", "status": "open"});
        let result = apply_resolution(&c, &ResolutionStrategy::Manual(merged.clone())).unwrap();
        assert_eq!(result.resolved_value, merged);
        assert_eq!(result.strategy_label, "manual");
    }

    #[test]
    fn field_level_resolution() {
        let c = make_conflict();
        let mut field_map = HashMap::new();
        field_map.insert("title".to_string(), FieldSource::Local);
        field_map.insert("status".to_string(), FieldSource::Remote);
        let result = apply_resolution(&c, &ResolutionStrategy::FieldLevel(field_map)).unwrap();
        assert_eq!(result.resolved_value["title"], "local title");
        assert_eq!(result.resolved_value["status"], "closed");
        assert_eq!(result.strategy_label, "field_level");
    }

    #[test]
    fn resolved_hash_is_hash_of_resolved_value() {
        let c = make_conflict();
        let result = apply_resolution(&c, &ResolutionStrategy::LocalWins).unwrap();
        let expected = hash_value(&result.resolved_value);
        assert_eq!(result.resolved_hash, expected);
    }
}
