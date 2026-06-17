use agileplus_p2p::discovery::PeerStatus;
use agileplus_p2p::discovery::discover_peers;
use agileplus_p2p::vector_clock::SyncVector;

use crate::device::args::StatusArgs;
use crate::device::types::{DeviceStatusReport, KnownPeerEntry, LocalDeviceInfo, VectorEntry};

/// Run the `device status` subcommand.
#[cfg(unix)]
pub async fn run_status(args: &StatusArgs) -> anyhow::Result<()> {
    let hostname = hostname::get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_else(|| "unknown".to_string());

    let local = LocalDeviceInfo {
        device_id: format!("local-{}", &hostname),
        hostname: hostname.clone(),
        tailscale_ip: String::from("(unavailable without Tailscale)"),
    };

    let local_vector = SyncVector::new(&local.device_id);
    let sync_vector: Vec<VectorEntry> = local_vector
        .entries
        .iter()
        .map(|((et, eid), seq)| VectorEntry {
            entity_type: et.clone(),
            entity_id: eid.clone(),
            last_sequence: *seq,
        })
        .collect();

    let peers_result: Result<Vec<_>, _> = discover_peers().await;
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

    let pending_outbound_events = 0usize;

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
        println!("Local Device");
        println!("  device_id   : {}", report.local.device_id);
        println!("  hostname    : {}", report.local.hostname);
        println!("  tailscale_ip: {}", report.local.tailscale_ip);
        println!();
    }

    if !args.peers_only {
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
        println!(
            "Pending Outbound Events: {}",
            report.pending_outbound_events
        );
        println!();
    }

    if !args.vectors_only {
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
