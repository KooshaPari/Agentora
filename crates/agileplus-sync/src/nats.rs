//! NATS pub/sub integration for sync events.
//!
//! Traceability: FR-SYNC-NATS / WP09-T058

use async_nats::Client;
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use tracing::{debug, error, info};

use crate::error::SyncError;

/// Subject for inbound webhook events from Plane.so.
pub const SUBJECT_INBOUND: &str = "agileplus.sync.plane.inbound";
/// Subject for outbound sync commands to Plane.so.
pub const SUBJECT_OUTBOUND: &str = "agileplus.sync.plane.outbound";
/// JetStream stream name for durable sync events.
pub const STREAM_NAME: &str = "AGILEPLUS_SYNC";

/// Envelope for messages published to the outbound sync subject.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutboundSyncCommand {
    /// Entity type being synced (e.g., "feature", "work_package").
    pub entity_type: String,
    /// Local entity identifier.
    pub entity_id: i64,
    /// Operation being requested (e.g., "create", "update", "delete").
    pub operation: String,
    /// Serialised entity payload.
    pub payload: serde_json::Value,
}

/// Envelope for inbound webhook messages from Plane.so.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InboundSyncEvent {
    /// Plane.so issue identifier.
    pub plane_issue_id: String,
    /// Event type (e.g., "issue.created", "issue.updated").
    pub event_type: String,
    /// Raw payload from Plane.so webhook.
    pub payload: serde_json::Value,
}

/// Thin wrapper around a NATS `Client` providing sync-specific publish and
/// subscribe helpers.
///
/// JetStream durability is set up during construction via [`NatsSyncBridge::new`].
pub struct NatsSyncBridge {
    client: Client,
}

impl NatsSyncBridge {
    /// Connect to NATS and ensure the `AGILEPLUS_SYNC` JetStream stream exists.
    pub async fn new(nats_url: &str) -> Result<Self, SyncError> {
        let client = async_nats::connect(nats_url)
            .await
            .map_err(|e| SyncError::Nats(e.into()))?;
        let bridge = Self { client };
        bridge.ensure_stream().await?;
        Ok(bridge)
    }

    /// Build a bridge from an already-connected `Client` (useful in tests /
    /// when the caller owns the connection).
    pub async fn from_client(client: Client) -> Result<Self, SyncError> {
        let bridge = Self { client };
        bridge.ensure_stream().await?;
        Ok(bridge)
    }

    /// Ensure the JetStream stream `AGILEPLUS_SYNC` exists, creating it if
    /// necessary.
    async fn ensure_stream(&self) -> Result<(), SyncError> {
        use async_nats::jetstream;
        let js = jetstream::new(self.client.clone());
        let stream_config = jetstream::stream::Config {
            name: STREAM_NAME.to_string(),
            subjects: vec![SUBJECT_INBOUND.to_string(), SUBJECT_OUTBOUND.to_string()],
            ..Default::default()
        };
        match js.get_or_create_stream(stream_config).await {
            Ok(_) => {
                info!(stream = STREAM_NAME, "JetStream stream ready");
                Ok(())
            }
            Err(e) => {
                error!(stream = STREAM_NAME, error = %e, "Failed to ensure JetStream stream");
                Err(SyncError::Nats(Box::new(e)))
            }
        }
    }

    /// Publish an outbound sync command to `agileplus.sync.plane.outbound`.
    pub async fn publish_outbound(&self, cmd: &OutboundSyncCommand) -> Result<(), SyncError> {
        let payload = serde_json::to_vec(cmd)?;
        self.client
            .publish(SUBJECT_OUTBOUND, payload.into())
            .await
            .map_err(|e| SyncError::Nats(e.into()))?;
        debug!(
            entity_type = %cmd.entity_type,
            entity_id = cmd.entity_id,
            operation = %cmd.operation,
            "Published outbound sync command"
        );
        Ok(())
    }

    /// Subscribe to `agileplus.sync.plane.inbound` and invoke `handler` for
    /// each message received.
    ///
    /// The subscription runs until `handler` returns `Err` or the stream ends.
    pub async fn subscribe_inbound<F, Fut>(&self, handler: F) -> Result<(), SyncError>
    where
        F: Fn(InboundSyncEvent) -> Fut + Send + Sync,
        Fut: std::future::Future<Output = Result<(), SyncError>> + Send,
    {
        let mut sub = self
            .client
            .subscribe(SUBJECT_INBOUND)
            .await
            .map_err(|e| SyncError::Nats(e.into()))?;
        info!(
            subject = SUBJECT_INBOUND,
            "Subscribed to inbound sync events"
        );

        while let Some(msg) = sub.next().await {
            match serde_json::from_slice::<InboundSyncEvent>(&msg.payload) {
                Ok(event) => {
                    debug!(plane_issue_id = %event.plane_issue_id, "Received inbound event");
                    if let Err(e) = handler(event).await {
                        error!(error = %e, "Handler error processing inbound event");
                        return Err(e);
                    }
                }
                Err(e) => {
                    error!(error = %e, "Failed to deserialise inbound sync event");
                }
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn outbound_command_serialises() {
        let cmd = OutboundSyncCommand {
            entity_type: "feature".to_string(),
            entity_id: 1,
            operation: "update".to_string(),
            payload: json!({"title": "hello"}),
        };
        let bytes = serde_json::to_vec(&cmd).unwrap();
        let back: OutboundSyncCommand = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(back.entity_type, "feature");
        assert_eq!(back.operation, "update");
    }

    #[test]
    fn inbound_event_serialises() {
        let ev = InboundSyncEvent {
            plane_issue_id: "plane-123".to_string(),
            event_type: "issue.updated".to_string(),
            payload: json!({"status": "done"}),
        };
        let bytes = serde_json::to_vec(&ev).unwrap();
        let back: InboundSyncEvent = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(back.plane_issue_id, "plane-123");
    }

    #[test]
    fn subject_constants() {
        assert!(SUBJECT_INBOUND.starts_with("agileplus.sync"));
        assert!(SUBJECT_OUTBOUND.starts_with("agileplus.sync"));
        assert_ne!(SUBJECT_INBOUND, SUBJECT_OUTBOUND);
    }
}
