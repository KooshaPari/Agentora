//! Time utilities library

pub use chrono::{DateTime, Utc};

/// Get current timestamp
pub fn now() -> DateTime<Utc> {
    Utc::now()
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_now() {
        let _ = now();
    }
}
