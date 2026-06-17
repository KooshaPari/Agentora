//! SyncReport — audit summary for a single sync run.
//!
//! Traceability: FR-SYNC-REPORT / WP09-T057

use std::fmt;
use std::time::Duration;

use crate::conflict::SyncConflict;
use crate::error::SyncError;

/// Summary of a completed sync operation, suitable for CLI output and audit logging.
#[derive(Debug, Default)]
pub struct SyncReport {
    /// Entities created during this sync run: `(entity_type, entity_id)`.
    pub created: Vec<(String, i64)>,
    /// Entities updated during this sync run.
    pub updated: Vec<(String, i64)>,
    /// Entities skipped (no changes detected).
    pub skipped: Vec<(String, i64)>,
    /// Conflicts detected but not yet resolved.
    pub conflicts: Vec<SyncConflict>,
    /// Errors encountered during sync.
    pub errors: Vec<SyncError>,
    /// Wall-clock duration of the sync run.
    pub duration: Duration,
}

impl SyncReport {
    /// Create an empty report.
    pub fn new() -> Self {
        Self::default()
    }

    /// Total number of entities processed (created + updated + skipped + conflicts + errors).
    pub fn total_processed(&self) -> usize {
        self.created.len()
            + self.updated.len()
            + self.skipped.len()
            + self.conflicts.len()
            + self.errors.len()
    }

    /// Returns `true` when no conflicts or errors were recorded.
    pub fn is_clean(&self) -> bool {
        self.conflicts.is_empty() && self.errors.is_empty()
    }
}

impl fmt::Display for SyncReport {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let sep = "─".repeat(52);
        writeln!(f, "┌{sep}┐")?;
        writeln!(f, "│  AgilePlus Sync Report{:>29}│", "")?;
        writeln!(f, "├{sep}┤")?;
        writeln!(f, "│  {:<20} {:>28}│", "Created", self.created.len())?;
        writeln!(f, "│  {:<20} {:>28}│", "Updated", self.updated.len())?;
        writeln!(f, "│  {:<20} {:>28}│", "Skipped", self.skipped.len())?;
        writeln!(f, "│  {:<20} {:>28}│", "Conflicts", self.conflicts.len())?;
        writeln!(f, "│  {:<20} {:>28}│", "Errors", self.errors.len())?;
        writeln!(
            f,
            "│  {:<20} {:>26.3}s│",
            "Duration",
            self.duration.as_secs_f64()
        )?;
        writeln!(f, "└{sep}┘")?;

        if !self.conflicts.is_empty() {
            writeln!(f, "\nConflicts:")?;
            for c in &self.conflicts {
                writeln!(
                    f,
                    "  • {}/{} — local={} remote={}",
                    c.entity_type,
                    c.entity_id,
                    &c.local_hash[..8],
                    &c.remote_hash[..8]
                )?;
            }
        }

        if !self.errors.is_empty() {
            writeln!(f, "\nErrors:")?;
            for e in &self.errors {
                writeln!(f, "  • {e}")?;
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn empty_report_is_clean() {
        let r = SyncReport::new();
        assert!(r.is_clean());
        assert_eq!(r.total_processed(), 0);
    }

    #[test]
    fn report_totals() {
        let mut r = SyncReport::new();
        r.created.push(("feature".into(), 1));
        r.updated.push(("wp".into(), 2));
        r.skipped.push(("feature".into(), 3));
        r.duration = Duration::from_millis(1234);
        assert_eq!(r.total_processed(), 3);
        assert!(r.is_clean());
    }

    #[test]
    fn report_display_contains_created() {
        let mut r = SyncReport::new();
        r.created.push(("feature".into(), 99));
        r.duration = Duration::from_secs(1);
        let s = r.to_string();
        assert!(s.contains("Created"));
        assert!(s.contains('1'));
    }
}
