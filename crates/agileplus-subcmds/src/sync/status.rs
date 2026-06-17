use anyhow::Result;
use chrono::{Duration, Utc};

use super::{args::SyncStatusArgs, helpers::format_age, types::SyncStatusRow};

/// Run `agileplus sync status`.
pub fn run_sync_status(args: SyncStatusArgs) -> Result<()> {
    let rows = vec![
        SyncStatusRow {
            entity_kind: "Feature".to_string(),
            entity_name: "auth-flow".to_string(),
            local_state: "implementing".to_string(),
            remote_state: Some("in_progress".to_string()),
            last_synced: Some(Utc::now() - Duration::minutes(2)),
            in_sync: true,
            conflict_count: 0,
        },
        SyncStatusRow {
            entity_kind: "Feature".to_string(),
            entity_name: "api-design".to_string(),
            local_state: "researched".to_string(),
            remote_state: Some("unstarted".to_string()),
            last_synced: Some(Utc::now() - Duration::hours(2)),
            in_sync: false,
            conflict_count: 1,
        },
        SyncStatusRow {
            entity_kind: "WP".to_string(),
            entity_name: "database-schema".to_string(),
            local_state: "specified".to_string(),
            remote_state: Some("backlog".to_string()),
            last_synced: Some(Utc::now() - Duration::hours(24)),
            in_sync: true,
            conflict_count: 0,
        },
    ];

    if args.output == "json" {
        println!("{}", serde_json::to_string_pretty(&rows)?);
        return Ok(());
    }

    let header = format!(
        "{:<26} | {:<14} | {:<14} | {:<12} | {:<5} | {}",
        "Entity", "Local State", "Remote State", "Last Synced", "Match", "Conflicts"
    );
    let sep = "\u{2500}".repeat(header.len());
    println!("{header}");
    println!("{sep}");

    for row in &rows {
        let entity = format!("{}: {}", row.entity_kind, row.entity_name);
        let remote = row.remote_state.as_deref().unwrap_or("—");
        let last_synced = row
            .last_synced
            .map(format_age)
            .unwrap_or("never".to_string());
        let match_icon = if row.conflict_count > 0 {
            "\u{2717}"
        } else if row.in_sync {
            "\u{2713}"
        } else {
            "~"
        };

        println!(
            "{:<26} | {:<14} | {:<14} | {:<12} | {:<5} | {}",
            entity, row.local_state, remote, last_synced, match_icon, row.conflict_count,
        );
    }
    Ok(())
}
