//! Core types for rate limiting

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Quota {
    pub permits: u32,
    pub window: Duration,
    pub burst: Option<u32>,
}

impl Quota {
    pub fn new(permits: u32, window: Duration) -> Self {
        Self {
            permits,
            window,
            burst: None,
        }
    }

    pub fn with_burst(mut self, burst: u32) -> Self {
        self.burst = Some(burst);
        self
    }

    pub fn per_second(permits: u32) -> Self {
        Self::new(permits, Duration::from_secs(1))
    }
    pub fn per_minute(permits: u32) -> Self {
        Self::new(permits, Duration::from_secs(60))
    }
    pub fn per_hour(permits: u32) -> Self {
        Self::new(permits, Duration::from_secs(3600))
    }

    pub fn burst_capacity(&self) -> u32 {
        self.burst.unwrap_or(self.permits)
    }
    pub fn refill_rate_per_second(&self) -> f64 {
        self.permits as f64 / self.window.as_secs_f64()
    }
}

impl Default for Quota {
    fn default() -> Self {
        Self::per_second(100)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct RateLimitStatus {
    pub allowed: bool,
    pub remaining: u32,
    pub limit: u32,
    pub reset_after: Duration,
    pub retry_after: Option<Duration>,
}

impl RateLimitStatus {
    pub fn allowed(remaining: u32, limit: u32, reset_after: Duration) -> Self {
        Self {
            allowed: true,
            remaining,
            limit,
            reset_after,
            retry_after: None,
        }
    }

    pub fn denied(limit: u32, retry_after: Duration) -> Self {
        Self {
            allowed: false,
            remaining: 0,
            limit,
            reset_after: retry_after,
            retry_after: Some(retry_after),
        }
    }

    pub fn is_allowed(&self) -> bool {
        self.allowed
    }
    pub fn is_denied(&self) -> bool {
        !self.allowed
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    pub quota: Quota,
    pub fail_open: bool,
    pub key_prefix: Option<String>,
    pub enable_warnings: bool,
    pub warning_threshold: f64,
}

impl RateLimitConfig {
    pub fn new(quota: Quota) -> Self {
        Self {
            quota,
            fail_open: false,
            key_prefix: None,
            enable_warnings: true,
            warning_threshold: 0.8,
        }
    }

    pub fn fail_open(mut self, fail_open: bool) -> Self {
        self.fail_open = fail_open;
        self
    }

    pub fn with_prefix(mut self, prefix: impl Into<String>) -> Self {
        self.key_prefix = Some(prefix.into());
        self
    }
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self::new(Quota::default())
    }
}
