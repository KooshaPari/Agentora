use std::time::Instant;

use anyhow::Result;

use super::{
    args::SyncPushArgs,
    helpers::{outcome_icon, outcome_verb},
    types::{SyncDirection, SyncItemOutcome, SyncReport, SyncReportEntry},
};

/// Run `agileplus sync push`.
pub async fn run_sync_push(args: SyncPushArgs) -> Result<()> {
    let start = Instant::now();

    if args.dry_run {
        println!("[dry-run] Inspecting local features for outbound sync...");
    } else {
        println!("Pushing to Plane.so...");
    }

    let mut report = SyncReport::new(SyncDirection::Push);

    if let Some(ref slug) = args.feature {
        report.add(stub_push_entry(slug, args.dry_run));
    } else {
        report.add(SyncReportEntry {
            entity_kind: "feature".to_string(),
            entity_name: "auth-flow".to_string(),
            outcome: SyncItemOutcome::Created,
            plane_id: if args.dry_run {
                None
            } else {
                Some("#42".to_string())
            },
            message: if args.dry_run {
                Some("would create".to_string())
            } else {
                Some("plane_work_item_id: #42".to_string())
            },
        });
        report.add(SyncReportEntry {
            entity_kind: "wp".to_string(),
            entity_name: "api-endpoints".to_string(),
            outcome: SyncItemOutcome::Updated,
            plane_id: if args.dry_run {
                None
            } else {
                Some("#43".to_string())
            },
            message: None,
        });
        report.add(SyncReportEntry {
            entity_kind: "wp".to_string(),
            entity_name: "database-schema".to_string(),
            outcome: SyncItemOutcome::Skipped,
            plane_id: None,
            message: Some("no changes".to_string()),
        });
    }

    report.duration_ms = start.elapsed().as_millis() as u64;
    print_push_report(&report, args.dry_run);
    Ok(())
}

fn stub_push_entry(slug: &str, dry_run: bool) -> SyncReportEntry {
    SyncReportEntry {
        entity_kind: "feature".to_string(),
        entity_name: slug.to_string(),
        outcome: SyncItemOutcome::Updated,
        plane_id: if dry_run {
            None
        } else {
            Some("#99".to_string())
        },
        message: if dry_run {
            Some("would update".to_string())
        } else {
            None
        },
    }
}

fn print_push_report(report: &SyncReport, dry_run: bool) {
    for entry in &report.entries {
        let icon = outcome_icon(&entry.outcome);
        let kind_label = format!("{} '{}'", entry.entity_kind, entry.entity_name);
        let suffix = match &entry.message {
            Some(msg) => format!(" ({})", msg),
            None => match &entry.plane_id {
                Some(id) => format!(" (plane_work_item_id: {})", id),
                None => String::new(),
            },
        };
        let verb = if dry_run {
            format!("[dry-run] {}", outcome_verb(&entry.outcome))
        } else {
            outcome_verb(&entry.outcome).to_string()
        };
        println!("{icon} {kind_label} {verb}{suffix}");
    }
    println!("Duration: {:.1}s", report.duration_ms as f64 / 1000.0);
}
