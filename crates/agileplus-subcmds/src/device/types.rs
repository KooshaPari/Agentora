use agileplus_p2p::discovery::{PeerInfo, PeerStatus};
use serde::Serialize;

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
