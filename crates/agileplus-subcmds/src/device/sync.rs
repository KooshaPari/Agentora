use std::time::Instant;

use agileplus_p2p::discovery::{PeerInfo, PeerStatus, discover_peers};
use agileplus_p2p::vector_clock::SyncVector;

use crate::device::args::SyncArgs;
use crate::device::types::PeerSyncReport;

/// Run the `device sync` subcommand.
#[cfg(unix)]
pub async fn run_sync(args: &SyncArgs) -> anyhow::Result<()> {
    if !args.all && args.peer.is_none() {
        anyhow::bail!(
            "No sync target specified.\n\
             Usage:\n  \
             agileplus device sync --all                  sync with all online peers\n  \
             agileplus device sync --peer <device-id>     sync with a specific peer"
        );
    }

    let all_peers: Vec<PeerInfo> = discover_peers()
        .await
        .map_err(|e| anyhow::anyhow!("Tailscale unavailable: {e}"))?;

    if all_peers.is_empty() {
        anyhow::bail!("No peers found on the Tailscale network.");
    }

    let target_peers: Vec<&PeerInfo> = if args.all {
        all_peers
            .iter()
            .filter(|p| p.status == PeerStatus::Online)
            .collect()
    } else {
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

    let local_device_id = hostname::get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_else(|| "local".to_string());

    let local_vector = SyncVector::new(&local_device_id);
    let mut reports: Vec<PeerSyncReport> = Vec::new();

    for peer in &target_peers {
        if args.verbose {
            println!("Syncing with {} ({}) …", peer.device_id, peer.tailscale_ip);
        }
        let t0 = Instant::now();

        let result: Result<agileplus_p2p::replication::ReplicationResult, _> =
            agileplus_p2p::replication::replicate_events(&local_device_id, peer, vec![]).await;

        let duration_ms = t0.elapsed().as_millis() as u64;

        match result {
            Ok(rep) => {
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
