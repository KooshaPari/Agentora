//! Inbound port traits

/// Inbound port trait
pub trait InboundPort: Send + Sync {
    /// Handle incoming message
    fn handle(&self, message: &[u8]) -> Result<Vec<u8>, String>;
}
