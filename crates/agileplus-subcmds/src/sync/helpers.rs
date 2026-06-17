use super::types::SyncItemOutcome;

pub(super) fn outcome_icon(outcome: &SyncItemOutcome) -> &'static str {
    match outcome {
        SyncItemOutcome::Created => "\u{2713}",
        SyncItemOutcome::Updated => "\u{2713}",
        SyncItemOutcome::Skipped => "\u{2296}",
        SyncItemOutcome::Conflict => "\u{26a0}",
        SyncItemOutcome::Imported => "\u{2713}",
    }
}

pub(super) fn outcome_verb(outcome: &SyncItemOutcome) -> &'static str {
    match outcome {
        SyncItemOutcome::Created => "created",
        SyncItemOutcome::Updated => "updated",
        SyncItemOutcome::Skipped => "skipped",
        SyncItemOutcome::Conflict => "conflict detected",
        SyncItemOutcome::Imported => "imported",
    }
}

pub(super) fn pull_verb(outcome: &SyncItemOutcome) -> &'static str {
    match outcome {
        SyncItemOutcome::Created | SyncItemOutcome::Imported => "imported",
        SyncItemOutcome::Updated => "updated",
        SyncItemOutcome::Skipped => "skipped",
        SyncItemOutcome::Conflict => "conflict detected",
    }
}

pub(super) fn capitalize(s: &str) -> String {
    let mut c = s.chars();
    match c.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().to_string() + c.as_str(),
    }
}

pub(super) fn format_age(dt: chrono::DateTime<chrono::Utc>) -> String {
    let secs = (chrono::Utc::now() - dt).num_seconds().max(0);
    if secs < 60 {
        format!("{secs}s ago")
    } else if secs < 3600 {
        format!("{}m ago", secs / 60)
    } else if secs < 86400 {
        format!("{}h ago", secs / 3600)
    } else {
        format!("{}d ago", secs / 86400)
    }
}
