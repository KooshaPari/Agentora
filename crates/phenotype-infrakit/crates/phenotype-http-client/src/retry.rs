//! Retry configuration and strategies
//!
//! Provides configurable retry logic with exponential backoff.

use std::time::Duration;

/// Retry configuration
#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Maximum number of retry attempts
    pub max_attempts: u32,
    /// Initial retry delay
    pub initial_delay: Duration,
    /// Maximum retry delay
    pub max_delay: Duration,
    /// Multiplier for exponential backoff
    pub backoff_multiplier: f64,
    /// HTTP status codes that should trigger a retry
    pub retry_status_codes: Vec<u16>,
    /// Enable retry
    pub enabled: bool,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(10),
            backoff_multiplier: 2.0,
            retry_status_codes: vec![
                408, // Request Timeout
                429, // Too Many Requests
                500, // Internal Server Error
                502, // Bad Gateway
                503, // Service Unavailable
                504, // Gateway Timeout
            ],
            enabled: true,
        }
    }
}

impl RetryConfig {
    /// Create a new retry configuration with defaults
    pub fn new() -> Self {
        Self::default()
    }

    /// Set max attempts
    pub fn with_max_attempts(mut self, max: u32) -> Self {
        self.max_attempts = max;
        self
    }

    /// Set initial delay
    pub fn with_initial_delay(mut self, delay: Duration) -> Self {
        self.initial_delay = delay;
        self
    }

    /// Set max delay
    pub fn with_max_delay(mut self, delay: Duration) -> Self {
        self.max_delay = delay;
        self
    }

    /// Set backoff multiplier
    pub fn with_backoff_multiplier(mut self, multiplier: f64) -> Self {
        self.backoff_multiplier = multiplier;
        self
    }

    /// Disable retry
    pub fn disabled(mut self) -> Self {
        self.enabled = false;
        self
    }

    /// Check if a status code should be retried
    pub fn should_retry_status(&self, status: u16) -> bool {
        self.retry_status_codes.contains(&status)
    }
}

/// Exponential backoff strategy
pub struct ExponentialBackoff {
    config: RetryConfig,
    attempt: u32,
}

impl ExponentialBackoff {
    /// Create a new exponential backoff with the given config
    pub fn new(config: RetryConfig) -> Self {
        Self { config, attempt: 0 }
    }

    /// Get the next delay duration
    pub fn next_delay(&mut self) -> Option<Duration> {
        if !self.config.enabled || self.attempt >= self.config.max_attempts {
            return None;
        }

        let delay_ms = self.config.initial_delay.as_millis() as f64
            * self.config.backoff_multiplier.powi(self.attempt as i32);

        let delay_ms = delay_ms.min(self.config.max_delay.as_millis() as f64);

        self.attempt += 1;
        Some(Duration::from_millis(delay_ms as u64))
    }

    /// Get current attempt number
    pub fn attempt(&self) -> u32 {
        self.attempt
    }

    /// Check if retries are exhausted
    pub fn is_exhausted(&self) -> bool {
        self.attempt >= self.config.max_attempts
    }

    /// Reset the backoff
    pub fn reset(&mut self) {
        self.attempt = 0;
    }
}

/// Retry strategy trait
pub trait RetryStrategy: Send + Sync {
    /// Determine if we should retry
    fn should_retry(&self, attempt: u32, error: &crate::Error) -> bool;
    /// Get the delay before the next retry
    fn delay(&self, attempt: u32) -> Duration;
}

/// Default retry strategy using exponential backoff
pub struct DefaultRetryStrategy {
    config: RetryConfig,
}

impl DefaultRetryStrategy {
    /// Create a new default retry strategy
    pub fn new(config: RetryConfig) -> Self {
        Self { config }
    }
}

impl RetryStrategy for DefaultRetryStrategy {
    fn should_retry(&self, attempt: u32, error: &crate::Error) -> bool {
        if !self.config.enabled || attempt >= self.config.max_attempts {
            return false;
        }

        match error {
            crate::Error::Timeout { .. } => true,
            crate::Error::Http { status, .. } => self.config.should_retry_status(*status),
            crate::Error::Network(_) => true,
            crate::Error::Connection(_) => true,
            _ => false,
        }
    }

    fn delay(&self, attempt: u32) -> Duration {
        let delay_ms = self.config.initial_delay.as_millis() as f64
            * self.config.backoff_multiplier.powi(attempt as i32);

        Duration::from_millis(delay_ms.min(self.config.max_delay.as_millis() as f64) as u64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_retry_config() {
        let config = RetryConfig::new()
            .with_max_attempts(5)
            .with_initial_delay(Duration::from_millis(200));

        assert_eq!(config.max_attempts, 5);
        assert_eq!(config.initial_delay, Duration::from_millis(200));
        assert!(config.should_retry_status(500));
        assert!(!config.should_retry_status(200));
    }

    #[test]
    fn test_exponential_backoff() {
        let config = RetryConfig::new()
            .with_initial_delay(Duration::from_millis(100))
            .with_backoff_multiplier(2.0);

        let mut backoff = ExponentialBackoff::new(config);

        assert_eq!(backoff.next_delay(), Some(Duration::from_millis(100)));
        assert_eq!(backoff.next_delay(), Some(Duration::from_millis(200)));
        assert_eq!(backoff.next_delay(), Some(Duration::from_millis(400)));
    }
}
