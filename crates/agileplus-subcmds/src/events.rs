//! CLI events subcommand for querying the AgilePlus event log.
//!
//! Provides `agileplus events` with filtering and output format options.
//!
//! Traceability: WP14-T088

use chrono::{DateTime, Utc};
use clap::Args;
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// CLI argument types
// ---------------------------------------------------------------------------

/// Output format for event listing.
#[derive(Debug, Clone, PartialEq, Eq, clap::ValueEnum, Default)]
pub enum EventOutputFormat {
    #[default]
    Table,
    Json,
    Jsonl,
}

/// Arguments for `agileplus events`.
#[derive(Debug, Args)]
pub struct EventsArgs {
    /// Filter events for a specific feature (by slug or id).
    #[arg(long)]
    pub feature: Option<String>,

    /// Show events since a duration or date (e.g. `1h`, `7d`, `2025-03-01`).
    #[arg(long)]
    pub since: Option<String>,

    /// Filter by event type (e.g. `feature_created`, `state_changed`).
    #[arg(long = "type", name = "type")]
    pub event_type: Option<String>,

    /// Filter by actor name (e.g. `spec-kitty`, `sync-oracle`).
    #[arg(long)]
    pub actor: Option<String>,

    /// Filter by entity type (e.g. `feature`, `work-package`).
    #[arg(long)]
    pub entity_type: Option<String>,

    /// Output format.
    #[arg(long, default_value = "table")]
    pub format: EventOutputFormat,

    /// Maximum number of events to return.
    #[arg(long, default_value_t = 50)]
    pub limit: usize,
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// A single event record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventRecord {
    pub id: u64,
    pub timestamp: DateTime<Utc>,
    pub event_type: String,
    pub entity_type: String,
    pub entity_id: u64,
    pub actor: String,
    pub summary: String,
    pub payload: serde_json::Value,
}

/// Result set from an event query.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventQueryResult {
    pub events: Vec<EventRecord>,
    pub total: usize,
}

// ---------------------------------------------------------------------------
// Filtering helpers
// ---------------------------------------------------------------------------

/// Parse a "since" string into an approximate cutoff `DateTime`.
///
/// Supports:
/// - Simple durations: `30m`, `1h`, `2h`, `7d`, `24h`
/// - ISO date strings: `2025-03-01`
pub fn parse_since(since: &str) -> Option<DateTime<Utc>> {
    let now = Utc::now();
    let s = since.trim();
    // Try duration shorthand.
    if let Some(rest) = s.strip_suffix('m') {
        if let Ok(mins) = rest.parse::<i64>() {
            return Some(now - chrono::Duration::minutes(mins));
        }
    }
    if let Some(rest) = s.strip_suffix('h') {
        if let Ok(hours) = rest.parse::<i64>() {
            return Some(now - chrono::Duration::hours(hours));
        }
    }
    if let Some(rest) = s.strip_suffix('d') {
        if let Ok(days) = rest.parse::<i64>() {
            return Some(now - chrono::Duration::days(days));
        }
    }
    // Try ISO date.
    if let Ok(dt) = chrono::NaiveDate::parse_from_str(s, "%Y-%m-%d") {
        return Some(DateTime::<Utc>::from_naive_utc_and_offset(
            dt.and_hms_opt(0, 0, 0).unwrap(),
            Utc,
        ));
    }
    None
}

/// Apply `EventsArgs` filters to a list of events.
pub fn filter_events(events: &[EventRecord], args: &EventsArgs) -> Vec<EventRecord> {
    let cutoff = args.since.as_deref().and_then(parse_since);
    events
        .iter()
        .filter(|e| {
            if let Some(ref cutoff_dt) = cutoff {
                if e.timestamp < *cutoff_dt {
                    return false;
                }
            }
            if let Some(ref et) = args.event_type {
                if &e.event_type != et {
                    return false;
                }
            }
            if let Some(ref actor) = args.actor {
                if &e.actor != actor {
                    return false;
                }
            }
            if let Some(ref ent) = args.entity_type {
                if &e.entity_type != ent {
                    return false;
                }
            }
            if let Some(ref feat) = args.feature {
                // Match entity_type == "feature" and entity_id or summary containing slug.
                if e.entity_type != "feature" {
                    return false;
                }
                if !e.summary.to_lowercase().contains(&feat.to_lowercase())
                    && e.entity_id.to_string() != *feat
                {
                    return false;
                }
            }
            true
        })
        .take(args.limit)
        .cloned()
        .collect()
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

/// Render events as a human-readable table.
pub fn render_table(events: &[EventRecord]) -> String {
    if events.is_empty() {
        return "No events found.\n".to_string();
    }
    let mut out = format!(
        "{:<21} | {:<17} | {:<18} | {:<11} | {}\n",
        "Time", "Entity", "Type", "Actor", "Summary"
    );
    out.push_str(&"─".repeat(89));
    out.push('\n');
    for e in events {
        let ts = e.timestamp.format("%Y-%m-%d %H:%M:%S").to_string();
        let entity = format!("{}: {}", capitalise(&e.entity_type), e.entity_id);
        out.push_str(&format!(
            "{:<21} | {:<17} | {:<18} | {:<11} | {}\n",
            ts, entity, e.event_type, e.actor, e.summary,
        ));
    }
    out
}

fn capitalise(s: &str) -> String {
    let mut c = s.chars();
    match c.next() {
        None => String::new(),
        Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
    }
}

/// Render events as a JSON array string.
pub fn render_json(events: &[EventRecord]) -> anyhow::Result<String> {
    Ok(serde_json::to_string_pretty(events)?)
}

/// Render events as newline-delimited JSON (one object per line).
pub fn render_jsonl(events: &[EventRecord]) -> anyhow::Result<String> {
    let mut out = String::new();
    for e in events {
        out.push_str(&serde_json::to_string(e)?);
        out.push('\n');
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

/// Run the `events` command.
///
/// In production this would query an agileplus-store or agileplus-events crate.
/// Here we use a stub that returns an empty result set, demonstrating the full
/// filter + render pipeline.
pub fn run_events(args: EventsArgs) -> anyhow::Result<()> {
    let all_events = load_events_stub();
    let filtered = filter_events(&all_events, &args);
    let result = EventQueryResult {
        total: filtered.len(),
        events: filtered.clone(),
    };

    let output = match args.format {
        EventOutputFormat::Table => render_table(&result.events),
        EventOutputFormat::Json => render_json(&result.events)?,
        EventOutputFormat::Jsonl => render_jsonl(&result.events)?,
    };
    print!("{output}");
    Ok(())
}

/// Stub event loader — returns a small canned dataset for tests and demos.
fn load_events_stub() -> Vec<EventRecord> {
    use chrono::TimeZone;
    vec![
        EventRecord {
            id: 1234,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 45, 30).unwrap(),
            event_type: "feature_created".to_string(),
            entity_type: "feature".to_string(),
            entity_id: 5,
            actor: "spec-kitty".to_string(),
            summary: "Auth Flow created".to_string(),
            payload: serde_json::json!({"title": "Auth Flow", "state": "created"}),
        },
        EventRecord {
            id: 1233,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 44, 15).unwrap(),
            event_type: "state_changed".to_string(),
            entity_type: "work-package".to_string(),
            entity_id: 8,
            actor: "sync-oracle".to_string(),
            summary: "database-schema: specified → implementing".to_string(),
            payload: serde_json::json!({"from": "specified", "to": "implementing"}),
        },
        EventRecord {
            id: 1232,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 43, 0).unwrap(),
            event_type: "sync_conflict".to_string(),
            entity_type: "feature".to_string(),
            entity_id: 5,
            actor: "platform".to_string(),
            summary: "Conflict detected (resolved: LocalWins)".to_string(),
            payload: serde_json::json!({"resolution": "LocalWins"}),
        },
        EventRecord {
            id: 1231,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 30, 0).unwrap(),
            event_type: "updated".to_string(),
            entity_type: "work-package".to_string(),
            entity_id: 7,
            actor: "user".to_string(),
            summary: "api-endpoints: description updated".to_string(),
            payload: serde_json::json!({}),
        },
        EventRecord {
            id: 1230,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 20, 45).unwrap(),
            event_type: "state_changed".to_string(),
            entity_type: "feature".to_string(),
            entity_id: 3,
            actor: "system".to_string(),
            summary: "api-design: researched → specified".to_string(),
            payload: serde_json::json!({"from": "researched", "to": "specified"}),
        },
    ]
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_args(since: Option<&str>, event_type: Option<&str>, actor: Option<&str>) -> EventsArgs {
        EventsArgs {
            feature: None,
            since: since.map(str::to_string),
            event_type: event_type.map(str::to_string),
            actor: actor.map(str::to_string),
            entity_type: None,
            format: EventOutputFormat::Table,
            limit: 50,
        }
    }

    #[test]
    fn test_parse_since_minutes() {
        let dt = parse_since("30m");
        assert!(dt.is_some());
        let elapsed = Utc::now() - dt.unwrap();
        assert!(elapsed.num_minutes() >= 29 && elapsed.num_minutes() <= 31);
    }

    #[test]
    fn test_parse_since_hours() {
        let dt = parse_since("2h");
        assert!(dt.is_some());
        let elapsed = Utc::now() - dt.unwrap();
        assert!(elapsed.num_hours() >= 1 && elapsed.num_hours() <= 3);
    }

    #[test]
    fn test_parse_since_days() {
        let dt = parse_since("7d");
        assert!(dt.is_some());
        let elapsed = Utc::now() - dt.unwrap();
        assert!(elapsed.num_days() >= 6 && elapsed.num_days() <= 8);
    }

    #[test]
    fn test_parse_since_iso_date() {
        let dt = parse_since("2025-03-01");
        assert!(dt.is_some());
    }

    #[test]
    fn test_parse_since_invalid() {
        assert!(parse_since("bogus").is_none());
    }

    #[test]
    fn test_filter_no_filters() {
        let events = load_events_stub();
        let args = make_args(None, None, None);
        let result = filter_events(&events, &args);
        assert_eq!(result.len(), events.len());
    }

    #[test]
    fn test_filter_by_actor() {
        let events = load_events_stub();
        let args = make_args(None, None, Some("spec-kitty"));
        let result = filter_events(&events, &args);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].actor, "spec-kitty");
    }

    #[test]
    fn test_filter_by_event_type() {
        let events = load_events_stub();
        let args = make_args(None, Some("state_changed"), None);
        let result = filter_events(&events, &args);
        assert_eq!(result.len(), 2);
        assert!(result.iter().all(|e| e.event_type == "state_changed"));
    }

    #[test]
    fn test_filter_limit() {
        let events = load_events_stub();
        let mut args = make_args(None, None, None);
        args.limit = 2;
        let result = filter_events(&events, &args);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_render_table_empty() {
        let out = render_table(&[]);
        assert!(out.contains("No events found"));
    }

    #[test]
    fn test_render_table_nonempty() {
        let events = load_events_stub();
        let out = render_table(&events[..1]);
        assert!(out.contains("feature_created"));
        assert!(out.contains("spec-kitty"));
    }

    #[test]
    fn test_render_json() {
        let events = load_events_stub();
        let json = render_json(&events[..1]).unwrap();
        assert!(json.contains("feature_created"));
        // Must be valid JSON array.
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert!(parsed.is_array());
    }

    #[test]
    fn test_render_jsonl() {
        let events = load_events_stub();
        let jsonl = render_jsonl(&events[..2]).unwrap();
        let lines: Vec<&str> = jsonl.trim_end().split('\n').collect();
        assert_eq!(lines.len(), 2);
        for line in lines {
            let v: serde_json::Value = serde_json::from_str(line).unwrap();
            assert!(v.is_object());
        }
    }

    #[test]
    fn test_run_events_table_does_not_err() {
        let args = EventsArgs {
            feature: None,
            since: None,
            event_type: None,
            actor: None,
            entity_type: None,
            format: EventOutputFormat::Table,
            limit: 10,
        };
        assert!(run_events(args).is_ok());
    }

    #[test]
    fn test_run_events_json_does_not_err() {
        let args = EventsArgs {
            feature: None,
            since: None,
            event_type: None,
            actor: None,
            entity_type: None,
            format: EventOutputFormat::Json,
            limit: 10,
        };
        assert!(run_events(args).is_ok());
    }
}
