//! Sliding window rate limiter adapter

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use parking_lot::RwLock;

use crate::error::Result;
use crate::ports::RateLimiterPort;
use crate::types::{Quota, RateLimitStatus};

#[derive(Debug, Clone)]
struct WindowState {
    timestamps: Vec<Instant>,
    capacity: u64,
    window_size: Duration,
}

#[derive(Debug)]
pub struct SlidingWindowAdapter {
    windows: Arc<RwLock<HashMap<String, WindowState>>>,
    quota: Quota,
    capacity: u64,
    window_size: Duration,
}

impl SlidingWindowAdapter {
    pub fn new(quota: Quota) -> Self {
        Self {
            windows: Arc::new(RwLock::new(HashMap::new())),
            capacity: quota.burst_capacity() as u64,
            window_size: quota.window,
            quota,
        }
    }

    fn purge_expired(state: &mut WindowState, now: Instant) {
        let cutoff = now - state.window_size;
        state.timestamps.retain(|&t| t > cutoff);
    }

    fn count_in_window(state: &WindowState) -> u64 {
        state.timestamps.len() as u64
    }

    fn reset_after(state: &WindowState, now: Instant) -> Duration {
        if let Some(&oldest) = state.timestamps.first() {
            let elapsed = now.duration_since(oldest);
            state.window_size.saturating_sub(elapsed)
        } else {
            Duration::from_secs(0)
        }
    }
}

#[async_trait]
impl RateLimiterPort for SlidingWindowAdapter {
    async fn acquire(&self, key: &str, permits: u32) -> Result<RateLimitStatus> {
        let now = Instant::now();
        let mut windows = self.windows.write();
        let state = windows
            .entry(key.to_string())
            .or_insert_with(|| WindowState {
                timestamps: Vec::new(),
                capacity: self.capacity,
                window_size: self.window_size,
            });
        Self::purge_expired(state, now);
        let count = Self::count_in_window(state);
        let available = state.capacity.saturating_sub(count);
        let permits = permits as u64;

        if available >= permits {
            for _ in 0..permits {
                state.timestamps.push(now);
            }
            let remaining = (state.capacity - count - permits) as u32;
            let reset_after = Self::reset_after(state, now);
            Ok(RateLimitStatus::allowed(
                remaining,
                state.capacity as u32,
                reset_after,
            ))
        } else {
            let reset_after = Self::reset_after(state, now);
            Ok(RateLimitStatus::denied(state.capacity as u32, reset_after))
        }
    }

    async fn check(&self, key: &str, permits: u32) -> Result<RateLimitStatus> {
        let now = Instant::now();
        let mut windows = self.windows.write();
        let state = windows
            .entry(key.to_string())
            .or_insert_with(|| WindowState {
                timestamps: Vec::new(),
                capacity: self.capacity,
                window_size: self.window_size,
            });
        Self::purge_expired(state, now);
        let count = Self::count_in_window(state);
        let available = state.capacity.saturating_sub(count);
        let permits = permits as u64;
        let remaining = available.saturating_sub(permits) as u32;
        let reset_after = Self::reset_after(state, now);

        if available >= permits {
            Ok(RateLimitStatus::allowed(
                remaining,
                state.capacity as u32,
                reset_after,
            ))
        } else {
            Ok(RateLimitStatus::denied(state.capacity as u32, reset_after))
        }
    }

    fn quota(&self) -> Quota {
        self.quota
    }

    async fn reset(&self, key: &str) -> Result<()> {
        if let Some(state) = self.windows.write().get_mut(key) {
            state.timestamps.clear();
        }
        Ok(())
    }

    async fn reset_all(&self) -> Result<()> {
        self.windows.write().clear();
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_sliding_window_acquire_allowed() {
        let adapter = SlidingWindowAdapter::new(Quota::new(10, Duration::from_secs(60)));
        let result = adapter.acquire("user:1", 1).await.unwrap();
        assert!(result.is_allowed());
        assert_eq!(result.remaining, 9);
    }

    #[tokio::test]
    async fn test_sliding_window_check() {
        let adapter = SlidingWindowAdapter::new(Quota::new(10, Duration::from_secs(60)));
        let result = adapter.check("user:1", 3).await.unwrap();
        assert!(result.is_allowed());
        assert_eq!(result.remaining, 7);
    }

    #[tokio::test]
    async fn test_sliding_window_exhausted() {
        let adapter = SlidingWindowAdapter::new(Quota::new(2, Duration::from_secs(60)));
        adapter.acquire("user:1", 2).await.unwrap();
        let result = adapter.check("user:1", 1).await.unwrap();
        assert!(result.is_denied());
        assert!(result.retry_after.is_some());
    }

    #[tokio::test]
    async fn test_sliding_window_reset() {
        let adapter = SlidingWindowAdapter::new(Quota::new(10, Duration::from_secs(60)));
        adapter.acquire("user:1", 10).await.unwrap();
        adapter.reset("user:1").await.unwrap();
        let result = adapter.acquire("user:1", 1).await.unwrap();
        assert!(result.is_allowed());
    }

    #[tokio::test]
    async fn test_sliding_window_reset_all() {
        let adapter = SlidingWindowAdapter::new(Quota::new(10, Duration::from_secs(60)));
        adapter.acquire("user:1", 5).await.unwrap();
        adapter.acquire("user:2", 5).await.unwrap();
        adapter.reset_all().await.unwrap();

        let result1 = adapter.check("user:1", 1).await.unwrap();
        let result2 = adapter.check("user:2", 1).await.unwrap();
        assert!(result1.is_allowed());
        assert!(result2.is_allowed());
    }
}
