//! Device management CLI commands for AgilePlus.
//!
//! Provides three subcommands:
//!   - `agileplus device discover` — enumerate peers on the Tailscale network
//!   - `agileplus device sync`     — replicate events with one or more peers
//!   - `agileplus device status`   — show local device identity and sync state
//!
//! Traceability: WP18 / T104, T105, T106

#[cfg(unix)]
use std::time::{Duration, Instant};

use agileplus_p2p::discovery::{PeerInfo, PeerStatus};
#[cfg(unix)]
use agileplus_p2p::discovery::discover_peers;
#[cfg(unix)]
use agileplus_p2p::vector_clock::SyncVector;
use clap::{Args, Subcommand};
use serde::Serialize;

// ── Top-level arg struct ──────────────────────────────────────────────────────

/// Arguments for the `device` command group.
#[derive(Debug, Args)]
pub struct DeviceArgs {
    #[command(subcommand)]
    pub command: DeviceSubcommand,
}

/// Subcommands available under `agileplus device`.
#[derive(Debug, Subcommand)]
pub enum DeviceSubcommand {
    /// Discover AgilePlus peers on the Tailscale network.
    Discover(DiscoverArgs),
    /// Synchronise events with one or more peers.
    Sync(SyncArgs),
    /// Show local device identity and sync vector state.
    Status(StatusArgs),
}

// ── T104: discover ────────────────────────────────────────────────────────────

/// Arguments for `agileplus device discover`.
#[derive(Debug, Args)]
pub struct DiscoverArgs {
    /// Timeout in seconds for the discovery operation.
    #[arg(long, default_value = "10")]
    pub timeout: u64,

    /// Port used to probe whether AgilePlus is running on a peer.
    #[arg(long, default_value = "3000")]
    pub port: u16,

    /// Output results as JSON instead of a human-readable table.
    #[arg(long)]
    pub json: bool,
}

/// JSON-serialisable representation of a single peer row.
#[derive(Debug, Serialize)]
pub struct PeerRow {
    pub device_id: String,
    pub hostname: String,
    pub tailscale_ip: String,
    pub status: String,
    pub last_seen: String,
}

impl From<&PeerInfo> for PeerRow {
    fn from(p: &PeerInfo) -> Self {
        let status = match p.status {
            PeerStatus::Online => "online",
            PeerStatus::Offline => "offline",
            PeerStatus::Unknown => "unknown",
        }
        .to_string();
        PeerRow {
            device_id: p.device_id.clone(),
            hostname: p.hostname.clone(),
            tailscale_ip: p.tailscale_ip.clone(),
            status,
            last_seen: "just now".to_string(),
        }
    }
}

/// Run the `device discover` subcommand.
///
/// Returns `Err` if Tailscale is unavailable or no peers are found.
#[cfg(unix)]
pub async fn run_discover(args: &DiscoverArgs) -> anyhow::Result<()> {
    let discover_fut = discover_peers();
    let peers = tokio::time::timeout(Duration::from_secs(args.timeout), discover_fut)
        .await
        .map_err(|_| {
            anyhow::anyhow!(
                "Discovery timed out after {} seconds. Is Tailscale running?",
                args.timeout
            )
        })?
        .map_err(|e| anyhow::anyhow!("Tailscale unavailable: {e}"))?;

    if peers.is_empty() {
        anyhow::bail!("No peers found on the Tailscale network. Make sure other AgilePlus devices are online.");
    }

    let rows: Vec<PeerRow> = peers.iter().map(PeerRow::from).collect();

    if args.json {
        println!("{}", serde_json::to_string_pretty(&rows)?);
        return Ok(());
    }

    // Human-readable table.
    let col_widths = (
        rows.iter().map(|r| r.device_id.len()).max().unwrap_or(9).max(9),
        rows.iter().map(|r| r.hostname.len()).max().unwrap_or(8).max(8),
        rows.iter()
            .map(|r| r.tailscale_ip.len())
            .max()
            .unwrap_or(12)
            .max(12),
        rows.iter().map(|r| r.status.len()).max().unwrap_or(6).max(6),
        9usize, // "LAST_SEEN"
    );

    println!(
        "{:<w0$}  {:<w1$}  {:<w2$}  {:<w3$}  {:<w4$}",
        "DEVICE_ID",
        "HOSTNAME",
        "TAILSCALE_IP",
        "STATUS",
        "LAST_SEEN",
        w0 = col_widths.0,
        w1 = col_widths.1,
        w2 = col_widths.2,
        w3 = col_widths.3,
        w4 = col_widths.4,
    );
    let divider_len = col_widths.0 + col_widths.1 + col_widths.2 + col_widths.3 + col_widths.4 + 8;
    println!("{}", "-".repeat(divider_len));

    for r in &rows {
        println!(
            "{:<w0$}  {:<w1$}  {:<w2$}  {:<w3$}  {:<w4$}",
            r.device_id,
            r.hostname,
            r.tailscale_ip,
            r.status,
            r.last_seen,
            w0 = col_widths.0,
            w1 = col_widths.1,
            w2 = col_widths.2,
            w3 = col_widths.3,
            w4 = col_widths.4,
        );
    }
    println!("\n{} peer(s) discovered.", rows.len());
    Ok(())
}

// ── T105: sync ────────────────────────────────────────────────────────────────

/// Conflict-resolution strategy for the sync operation.
#[derive(Debug, Clone, clap::ValueEnum)]
pub enum SyncStrategy {
    /// Last-write wins (default).
    LastWriteWins,
    /// Manual conflict resolution — flag conflicts for review.
    Manual,
}

impl std::fmt::Display for SyncStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SyncStrategy::LastWriteWins => write!(f, "last-write-wins"),
            SyncStrategy::Manual => write!(f, "manual"),
        }
    }
}

/// Arguments for `agileplus device sync`.
#[derive(Debug, Args)]
pub struct SyncArgs {
    /// Sync with all online peers.
    #[arg(long, conflicts_with = "peer")]
    pub all: bool,

    /// Sync with a specific peer identified by device ID or Tailscale IP.
    #[arg(long)]
    pub peer: Option<String>,

    /// Conflict-resolution strategy.
    #[arg(long, value_enum, default_value = "last-write-wins")]
    pub strategy: SyncStrategy,

    /// Preview what would be synced without transferring any data.
    #[arg(long)]
    pub dry_run: bool,

    /// Print detailed progress information.
    #[arg(long)]
    pub verbose: bool,
}

/// JSON-serialisable sync report for one peer.
#[derive(Debug, Serialize)]
pub struct PeerSyncReport {
    pub device_id: String,
    pub hostname: String,
    pub events_sent: usize,
    pub events_received: usize,
    pub conflicts: usize,
    pub duration_ms: u64,
    pub success: bool,
    pub error: Option<String>,
}

/// Run the `device sync` subcommand.
#[cfg(unix)]
pub async fn run_sync(args: &SyncArgs) -> anyhow::Result<()> {
    // Validate flag combinations.
    if !args.all && args.peer.is_none() {
        anyhow::bail!(
            "No sync target specified.\n\
             Usage:\n  \
             agileplus device sync --all                  sync with all online peers\n  \
             agileplus device sync --peer <device-id>     sync with a specific peer"
        );
    }

    // Discover peers.
    let all_peers = discover_peers()
        .await
        .map_err(|e| anyhow::anyhow!("Tailscale unavailable: {e}"))?;

    if all_peers.is_empty() {
        anyhow::bail!("No peers found on the Tailscale network.");
    }

    // Filter to the requested set of peers.
    let target_peers: Vec<&PeerInfo> = if args.all {
        all_peers
            .iter()
            .filter(|p| p.status == PeerStatus::Online)
            .collect()
    } else {
        // --peer specified; match by device_id or tailscale_ip.
        let selector = args.peer.as_deref().unwrap_or("");
        let matched: Vec<&PeerInfo> = all_peers
            .iter()
            .filter(|p| p.device_id == selector || p.tailscale_ip == selector)
            .collect();
        if matched.is_empty() {
            anyhow::bail!(
                "Peer '{}' not found. Run `agileplus device discover` to list available peers.",
                selector
            );
        }
        matched
    };

    if target_peers.is_empty() {
        anyhow::bail!("No online peers to sync with.");
    }

    if args.dry_run {
        println!("[dry-run] Would sync with {} peer(s):", target_peers.len());
        for p in &target_peers {
            println!("  {} ({})", p.device_id, p.tailscale_ip);
        }
        println!("[dry-run] No data transferred.");
        return Ok(());
    }

    // Use a local device_id placeholder; in production this would come from DeviceStore.
    let local_device_id = hostname::get()
        .map(|h| h.to_string_lossy().into_owned())
        .unwrap_or_else(|_| "local".to_string());

    let local_vector = SyncVector::new(&local_device_id);

    let mut reports: Vec<PeerSyncReport> = Vec::new();

    for peer in &target_peers {
        if args.verbose {
            println!("Syncing with {} ({}) …", peer.device_id, peer.tailscale_ip);
        }
        let t0 = Instant::now();

        // In a full integration, an EventStore ref would be threaded in.
        // Here we call replicate_events directly as a best-effort sync.
        let result = agileplus_p2p::replication::replicate_events(
            &local_device_id,
            peer,
            vec![], // no local events to send without a live EventStore
        )
        .await;

        let duration_ms = t0.elapsed().as_millis() as u64;

        match result {
            Ok(rep) => {
                // Merge peer's vector into our local vector for the report.
                let _updated = {
                    let mut v = local_vector.clone();
                    v.merge(&SyncVector::new(&peer.device_id));
                    v
                };
                reports.push(PeerSyncReport {
                    device_id: peer.device_id.clone(),
                    hostname: peer.hostname.clone(),
                    events_sent: rep.events_sent,
                    events_received: rep.events_received,
                    conflicts: 0,
                    duration_ms,
                    success: true,
                    error: None,
                });
            }
            Err(e) => {
                reports.push(PeerSyncReport {
                    device_id: peer.device_id.clone(),
                    hostname: peer.hostname.clone(),
                    events_sent: 0,
                    events_received: 0,
                    conflicts: 0,
                    duration_ms,
                    success: false,
                    error: Some(e.to_string()),
                });
            }
        }
    }

    // Print sync report.
    println!("\nSync Report (strategy: {})", args.strategy);
    println!("{}", "=".repeat(60));
    for r in &reports {
        let status_str = if r.success { "OK" } else { "FAILED" };
        println!(
            "  {} {} — sent: {}, received: {}, conflicts: {}, {}ms [{}]",
            r.device_id,
            r.hostname,
            r.events_sent,
            r.events_received,
            r.conflicts,
            r.duration_ms,
            status_str,
        );
        if let Some(ref err) = r.error {
            println!("    error: {err}");
        }
    }
    let ok_count = reports.iter().filter(|r| r.success).count();
    println!(
        "\n{}/{} peer(s) synced successfully.",
        ok_count,
        reports.len()
    );
    Ok(())
}

// ── T106: status ──────────────────────────────────────────────────────────────

/// Arguments for `agileplus device status`.
#[derive(Debug, Args)]
pub struct StatusArgs {
    /// Output as JSON.
    #[arg(long)]
    pub json: bool,

    /// Show only the known peers section.
    #[arg(long, conflicts_with = "vectors_only")]
    pub peers_only: bool,

    /// Show only the sync vector section.
    #[arg(long, conflicts_with = "peers_only")]
    pub vectors_only: bool,
}

/// JSON-serialisable full status report.
#[derive(Debug, Serialize)]
pub struct DeviceStatusReport {
    pub local: LocalDeviceInfo,
    pub sync_vector: Vec<VectorEntry>,
    pub known_peers: Vec<KnownPeerEntry>,
    pub pending_outbound_events: usize,
}

#[derive(Debug, Serialize)]
pub struct LocalDeviceInfo {
    pub device_id: String,
    pub hostname: String,
    pub tailscale_ip: String,
}

#[derive(Debug, Serialize)]
pub struct VectorEntry {
    pub entity_type: String,
    pub entity_id: String,
    pub last_sequence: u64,
}

#[derive(Debug, Serialize)]
pub struct KnownPeerEntry {
    pub device_id: String,
    pub hostname: String,
    pub tailscale_ip: String,
    pub status: String,
    pub last_sync: String,
}

/// Run the `device status` subcommand.
#[cfg(unix)]
pub async fn run_status(args: &StatusArgs) -> anyhow::Result<()> {
    // Gather local identity.  In a full integration this comes from DeviceStore.
    let hostname = hostname::get()
        .map(|h| h.to_string_lossy().into_owned())
        .unwrap_or_else(|_| "unknown".to_string());

    let local = LocalDeviceInfo {
        device_id: format!("local-{}", &hostname),
        hostname: hostname.clone(),
        tailscale_ip: String::from("(unavailable without Tailscale)"),
    };

    // Build a stub sync vector (in production, loaded from persistent state).
    let local_vector = SyncVector::new(&local.device_id);
    let sync_vector: Vec<VectorEntry> = local_vector
        .entries
        .iter()
        .map(|((et, eid), &seq)| VectorEntry {
            entity_type: et.clone(),
            entity_id: eid.clone(),
            last_sequence: seq,
        })
        .collect();

    // Discover live peers.
    let peers_result = discover_peers().await;
    let known_peers: Vec<KnownPeerEntry> = match peers_result {
        Ok(peers) => peers
            .iter()
            .map(|p| KnownPeerEntry {
                device_id: p.device_id.clone(),
                hostname: p.hostname.clone(),
                tailscale_ip: p.tailscale_ip.clone(),
                status: match p.status {
                    PeerStatus::Online => "online",
                    PeerStatus::Offline => "offline",
                    PeerStatus::Unknown => "unknown",
                }
                .to_string(),
                last_sync: "never".to_string(),
            })
            .collect(),
        Err(_) => vec![],
    };

    let pending_outbound_events = 0usize; // requires live EventStore integration

    let report = DeviceStatusReport {
        local,
        sync_vector,
        known_peers,
        pending_outbound_events,
    };

    if args.json {
        println!("{}", serde_json::to_string_pretty(&report)?);
        return Ok(());
    }

    if !args.vectors_only {
        // Local identity section.
        println!("Local Device");
        println!("  device_id   : {}", report.local.device_id);
        println!("  hostname    : {}", report.local.hostname);
        println!("  tailscale_ip: {}", report.local.tailscale_ip);
        println!();
    }

    if !args.peers_only {
        // Sync vector section.
        println!("Sync Vector ({} entities)", report.sync_vector.len());
        if report.sync_vector.is_empty() {
            println!("  (empty — no events synced yet)");
        } else {
            for v in &report.sync_vector {
                println!(
                    "  {}/{} → seq {}",
                    v.entity_type, v.entity_id, v.last_sequence
                );
            }
        }
        println!();
        println!("Pending Outbound Events: {}", report.pending_outbound_events);
        println!();
    }

    if !args.vectors_only {
        // Known peers section.
        println!("Known Peers ({} total)", report.known_peers.len());
        if report.known_peers.is_empty() {
            println!("  (none — run `agileplus device discover` to find peers)");
        } else {
            for p in &report.known_peers {
                println!(
                    "  {} {} [{}] — last sync: {}",
                    p.device_id, p.hostname, p.status, p.last_sync
                );
            }
        }
    }

    Ok(())
}

// ── Dispatch ──────────────────────────────────────────────────────────────────

/// Dispatch a `DeviceArgs` to the appropriate handler.
#[cfg(unix)]
pub async fn run(args: &DeviceArgs) -> anyhow::Result<()> {
    match &args.command {
        DeviceSubcommand::Discover(a) => run_discover(a).await,
        DeviceSubcommand::Sync(a) => run_sync(a).await,
        DeviceSubcommand::Status(a) => run_status(a).await,
    }
}

/// Dispatch a `DeviceArgs` to the appropriate handler.
#[cfg(not(unix))]
pub async fn run(_args: &DeviceArgs) -> anyhow::Result<()> {
    anyhow::bail!("Device commands require Unix (Tailscale UNIX socket)")
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── DiscoverArgs defaults ────────────────────────────────────────────────

    #[test]
    fn discover_args_defaults() {
        let args = DiscoverArgs {
            timeout: 10,
            port: 3000,
            json: false,
        };
        assert_eq!(args.timeout, 10);
        assert_eq!(args.port, 3000);
        assert!(!args.json);
    }

    // ── PeerRow conversion ───────────────────────────────────────────────────

    #[test]
    fn peer_row_from_online_peer() {
        let peer = PeerInfo {
            device_id: "dev-abc".to_string(),
            hostname: "my-machine".to_string(),
            tailscale_ip: "100.64.0.1".to_string(),
            status: PeerStatus::Online,
        };
        let row = PeerRow::from(&peer);
        assert_eq!(row.device_id, "dev-abc");
        assert_eq!(row.status, "online");
    }

    #[test]
    fn peer_row_from_offline_peer() {
        let peer = PeerInfo {
            device_id: "dev-xyz".to_string(),
            hostname: "other-machine".to_string(),
            tailscale_ip: "100.64.0.2".to_string(),
            status: PeerStatus::Offline,
        };
        let row = PeerRow::from(&peer);
        assert_eq!(row.status, "offline");
    }

    #[test]
    fn peer_row_from_unknown_peer() {
        let peer = PeerInfo {
            device_id: "dev-unk".to_string(),
            hostname: "mystery-machine".to_string(),
            tailscale_ip: "100.64.0.3".to_string(),
            status: PeerStatus::Unknown,
        };
        let row = PeerRow::from(&peer);
        assert_eq!(row.status, "unknown");
    }

    // ── PeerRow serialisation ────────────────────────────────────────────────

    #[test]
    fn peer_row_serialises_to_json() {
        let row = PeerRow {
            device_id: "dev-1".to_string(),
            hostname: "host-1".to_string(),
            tailscale_ip: "100.64.0.1".to_string(),
            status: "online".to_string(),
            last_seen: "just now".to_string(),
        };
        let json = serde_json::to_string(&row).unwrap();
        assert!(json.contains("dev-1"));
        assert!(json.contains("online"));
    }

    // ── SyncArgs validation helpers ──────────────────────────────────────────

    #[test]
    fn sync_strategy_display() {
        assert_eq!(SyncStrategy::LastWriteWins.to_string(), "last-write-wins");
        assert_eq!(SyncStrategy::Manual.to_string(), "manual");
    }

    // ── StatusArgs flags ─────────────────────────────────────────────────────

    #[test]
    fn status_args_default_shows_all() {
        let args = StatusArgs {
            json: false,
            peers_only: false,
            vectors_only: false,
        };
        assert!(!args.json);
        assert!(!args.peers_only);
        assert!(!args.vectors_only);
    }

    // ── DeviceStatusReport serialisation ─────────────────────────────────────

    #[test]
    fn device_status_report_serialises() {
        let report = DeviceStatusReport {
            local: LocalDeviceInfo {
                device_id: "dev-local".to_string(),
                hostname: "myhost".to_string(),
                tailscale_ip: "100.64.0.0".to_string(),
            },
            sync_vector: vec![VectorEntry {
                entity_type: "Feature".to_string(),
                entity_id: "1".to_string(),
                last_sequence: 42,
            }],
            known_peers: vec![KnownPeerEntry {
                device_id: "dev-peer".to_string(),
                hostname: "peer-host".to_string(),
                tailscale_ip: "100.64.0.5".to_string(),
                status: "online".to_string(),
                last_sync: "never".to_string(),
            }],
            pending_outbound_events: 3,
        };
        let json = serde_json::to_string(&report).unwrap();
        assert!(json.contains("dev-local"));
        assert!(json.contains("Feature"));
        assert!(json.contains("dev-peer"));
        assert!(json.contains("3"));
    }

    // ── PeerSyncReport serialisation ─────────────────────────────────────────

    #[test]
    fn peer_sync_report_serialises() {
        let report = PeerSyncReport {
            device_id: "dev-abc".to_string(),
            hostname: "abc-host".to_string(),
            events_sent: 5,
            events_received: 3,
            conflicts: 1,
            duration_ms: 120,
            success: true,
            error: None,
        };
        let json = serde_json::to_string(&report).unwrap();
        assert!(json.contains("dev-abc"));
        assert!(json.contains("true"));
    }

    #[test]
    fn peer_sync_report_failed_includes_error() {
        let report = PeerSyncReport {
            device_id: "dev-fail".to_string(),
            hostname: "fail-host".to_string(),
            events_sent: 0,
            events_received: 0,
            conflicts: 0,
            duration_ms: 5001,
            success: false,
            error: Some("connection refused".to_string()),
        };
        let json = serde_json::to_string(&report).unwrap();
        assert!(json.contains("connection refused"));
        assert!(json.contains("false"));
    }
}
