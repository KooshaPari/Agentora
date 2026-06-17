//! No-op [`TransportPort`] — mailbox transport stub for single-agent dispatch.

use async_trait::async_trait;
use substrate::domain::{Mailbox, Message};
use substrate::{SubstrateError, TransportPort};
use uuid::Uuid;

pub struct NoopTransport;

#[async_trait]
impl TransportPort for NoopTransport {
    async fn publish(&self, _message: &Message) -> substrate::Result<()> {
        Ok(())
    }

    async fn subscribe(&self, _owner: &str) -> substrate::Result<Vec<Message>> {
        Ok(vec![])
    }

    async fn claim(&self, _owner: &str, _message_id: &Uuid) -> substrate::Result<Message> {
        Err(SubstrateError::NotFound("noop transport".into()))
    }

    async fn mailbox(&self, owner: &str) -> substrate::Result<Mailbox> {
        Ok(Mailbox {
            owner: owner.into(),
            messages: vec![],
        })
    }
}
