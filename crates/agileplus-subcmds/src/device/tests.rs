use super::*;
use agileplus_p2p::discovery::{PeerInfo, PeerStatus};

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

#[test]
fn sync_strategy_display() {
    assert_eq!(SyncStrategy::LastWriteWins.to_string(), "last-write-wins");
    assert_eq!(SyncStrategy::Manual.to_string(), "manual");
}

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
