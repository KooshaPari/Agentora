use std::time::Duration;

use agileplus_p2p::discovery::{PeerInfo, discover_peers};

use crate::device::args::DiscoverArgs;
use crate::device::types::PeerRow;

/// Run the `device discover` subcommand.
///
/// Returns `Err` if Tailscale is unavailable or no peers are found.
#[cfg(unix)]
pub async fn run_discover(args: &DiscoverArgs) -> anyhow::Result<()> {
    let discover_fut = discover_peers();
    let peers: Vec<PeerInfo> =
        tokio::time::timeout(Duration::from_secs(args.timeout), discover_fut)
            .await
            .map_err(|_| {
                anyhow::anyhow!(
                    "Discovery timed out after {} seconds. Is Tailscale running?",
                    args.timeout
                )
            })?
            .map_err(|e| anyhow::anyhow!("Tailscale unavailable: {e}"))?;

    if peers.is_empty() {
        anyhow::bail!(
            "No peers found on the Tailscale network. Make sure other AgilePlus devices are online."
        );
    }

    let rows: Vec<PeerRow> = peers.iter().map(PeerRow::from).collect();

    if args.json {
        println!("{}", serde_json::to_string_pretty(&rows)?);
        return Ok(());
    }

    let col_widths = (
        rows.iter()
            .map(|r| r.device_id.len())
            .max()
            .unwrap_or(9)
            .max(9),
        rows.iter()
            .map(|r| r.hostname.len())
            .max()
            .unwrap_or(8)
            .max(8),
        rows.iter()
            .map(|r| r.tailscale_ip.len())
            .max()
            .unwrap_or(12)
            .max(12),
        rows.iter()
            .map(|r| r.status.len())
            .max()
            .unwrap_or(6)
            .max(6),
        9usize,
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
