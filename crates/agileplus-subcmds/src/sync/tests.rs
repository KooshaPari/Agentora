use super::*;
use tempfile::TempDir;

#[test]
fn sync_config_default() {
    let cfg = SyncConfig::default();
    assert!(!cfg.auto_sync_enabled);
}

#[test]
fn sync_config_save_and_load() {
    let tmp = TempDir::new().unwrap();
    let cfg = SyncConfig {
        auto_sync_enabled: true,
    };
    cfg.save(tmp.path()).unwrap();

    let loaded = SyncConfig::load(tmp.path()).unwrap();
    assert!(loaded.auto_sync_enabled);
}

#[test]
fn sync_config_load_missing() {
    let tmp = TempDir::new().unwrap();
    let cfg = SyncConfig::load(tmp.path()).unwrap();
    assert!(!cfg.auto_sync_enabled);
}

#[tokio::test]
async fn push_dry_run_all() {
    let args = SyncPushArgs {
        feature: None,
        dry_run: true,
    };
    assert!(run_sync_push(args).await.is_ok());
}

#[tokio::test]
async fn push_dry_run_single_feature() {
    let args = SyncPushArgs {
        feature: Some("my-feature".to_string()),
        dry_run: true,
    };
    assert!(run_sync_push(args).await.is_ok());
}

#[tokio::test]
async fn pull_dry_run() {
    let args = SyncPullArgs {
        feature: None,
        dry_run: true,
    };
    assert!(run_sync_pull(args).await.is_ok());
}

#[test]
fn status_table_output() {
    let args = SyncStatusArgs {
        output: "table".to_string(),
    };
    assert!(run_sync_status(args).is_ok());
}

#[test]
fn status_json_output() {
    let args = SyncStatusArgs {
        output: "json".to_string(),
    };
    assert!(run_sync_status(args).is_ok());
}

#[test]
fn format_age_seconds() {
    let now = chrono::Utc::now() - chrono::Duration::seconds(30);
    let s = helpers::format_age(now);
    assert!(s.ends_with("s ago"), "got: {s}");
}

#[test]
fn format_age_minutes() {
    let t = chrono::Utc::now() - chrono::Duration::minutes(5);
    let s = helpers::format_age(t);
    assert!(s.ends_with("m ago"), "got: {s}");
}

#[test]
fn format_age_hours() {
    let t = chrono::Utc::now() - chrono::Duration::hours(3);
    let s = helpers::format_age(t);
    assert!(s.ends_with("h ago"), "got: {s}");
}

#[test]
fn format_age_days() {
    let t = chrono::Utc::now() - chrono::Duration::days(2);
    let s = helpers::format_age(t);
    assert!(s.ends_with("d ago"), "got: {s}");
}

#[test]
fn sync_report_add_entries() {
    let mut r = SyncReport::new(SyncDirection::Push);
    r.add(SyncReportEntry {
        entity_kind: "feature".to_string(),
        entity_name: "foo".to_string(),
        outcome: SyncItemOutcome::Created,
        plane_id: Some("#1".to_string()),
        message: None,
    });
    assert_eq!(r.entries.len(), 1);
}

#[test]
fn capitalize_helper() {
    assert_eq!(helpers::capitalize("feature"), "Feature");
    assert_eq!(helpers::capitalize("wp"), "Wp");
    assert_eq!(helpers::capitalize(""), "");
}

#[test]
fn outcome_icons_and_verbs() {
    for outcome in [
        SyncItemOutcome::Created,
        SyncItemOutcome::Updated,
        SyncItemOutcome::Skipped,
        SyncItemOutcome::Conflict,
        SyncItemOutcome::Imported,
    ] {
        assert!(!helpers::outcome_icon(&outcome).is_empty());
        assert!(!helpers::outcome_verb(&outcome).is_empty());
        assert!(!helpers::pull_verb(&outcome).is_empty());
    }
}
