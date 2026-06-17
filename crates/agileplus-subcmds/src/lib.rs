//! AgilePlus hidden sub-commands registry.
//!
//! Defines ~25 sub-commands invocable via Claude Code's SlashCommand tool,
//! organized into 7 categories. Each invocation is logged to an append-only
//! JSONL audit trail.
//!
//! Traceability: FR-048, FR-049 / WP20

pub mod audit;
pub mod dashboard;
pub mod events;
pub mod platform;
pub mod registry;
pub mod sync;

pub use audit::AuditLog;
pub use dashboard::{
    DashboardArgs, DashboardOpenArgs, DashboardPortArgs, DashboardSubcommand, api_reachable,
    configured_port, dashboard_url, run_dashboard, run_dashboard_open, run_dashboard_port,
};
pub use events::{
    EventOutputFormat, EventQueryResult, EventRecord, EventsArgs, filter_events, parse_since,
    render_json, render_jsonl, render_table, run_events,
};
pub use platform::{
    OverallStatus, PlatformArgs, PlatformDownArgs, PlatformHealth, PlatformLogsArgs,
    PlatformStatusArgs, PlatformSubcommand, PlatformUpArgs, ServiceHealth, ServiceStatus,
    run_platform, run_platform_down, run_platform_logs, run_platform_status, run_platform_up,
};
pub use registry::{SubCommand, SubCommandCategory, SubCommandRegistry};
pub use sync::{
    AutoSyncAction, ConflictResolution, SyncArgs, SyncAutoArgs, SyncConfig, SyncConflict,
    SyncDirection, SyncItemOutcome, SyncPullArgs, SyncPushArgs, SyncReport, SyncReportEntry,
    SyncResolveArgs, SyncStatusArgs, SyncStatusRow, SyncSubcommand, run_sync,
};
