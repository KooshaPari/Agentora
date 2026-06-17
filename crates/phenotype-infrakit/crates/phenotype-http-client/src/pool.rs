//! Connection pool configuration and management
//!
//! Provides connection pooling for efficient reuse of HTTP connections.

use std::time::Duration;

/// Connection pool configuration
#[derive(Debug, Clone)]
pub struct PoolConfig {
    /// Maximum number of idle connections per host
    pub max_idle_per_host: usize,
    /// Maximum number of connections total
    pub max_connections: usize,
    /// Idle connection timeout
    pub idle_timeout: Duration,
    /// Connection timeout
    pub connection_timeout: Duration,
    /// Enable connection pooling
    pub enabled: bool,
}

impl Default for PoolConfig {
    fn default() -> Self {
        Self {
            max_idle_per_host: 10,
            max_connections: 100,
            idle_timeout: Duration::from_secs(90),
            connection_timeout: Duration::from_secs(30),
            enabled: true,
        }
    }
}

impl PoolConfig {
    /// Create a new pool configuration with defaults
    pub fn new() -> Self {
        Self::default()
    }

    /// Set max idle connections per host
    pub fn with_max_idle_per_host(mut self, max: usize) -> Self {
        self.max_idle_per_host = max;
        self
    }

    /// Set max total connections
    pub fn with_max_connections(mut self, max: usize) -> Self {
        self.max_connections = max;
        self
    }

    /// Set idle timeout
    pub fn with_idle_timeout(mut self, timeout: Duration) -> Self {
        self.idle_timeout = timeout;
        self
    }

    /// Disable pooling
    pub fn disabled(mut self) -> Self {
        self.enabled = false;
        self
    }
}
