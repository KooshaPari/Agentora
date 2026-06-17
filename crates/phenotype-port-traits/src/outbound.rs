//! Outbound port traits

/// Outbound port trait
pub trait OutboundPort: Send + Sync {
    /// Send outgoing message
    fn send(&self, message: &[u8]) -> Result<(), String>;
}
