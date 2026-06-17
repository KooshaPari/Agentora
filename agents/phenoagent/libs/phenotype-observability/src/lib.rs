//! Observability utilities for Phenotype

use std::time::{Duration, Instant};

/// Timer for measuring operation duration
pub struct Timer {
    start: Instant,
}

impl Timer {
    /// Create a new timer
    pub fn new() -> Self {
        Self {
            start: Instant::now(),
        }
    }
    
    /// Get elapsed time
    pub fn elapsed(&self) -> Duration {
        self.start.elapsed()
    }
}

impl Default for Timer {
    fn default() -> Self {
        Self::new()
    }
}
