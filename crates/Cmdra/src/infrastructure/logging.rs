//! Logging infrastructure

use crate::domain::Logger;
use crate::infrastructure::tracing::init_tracing;
use tracing::{debug, error, info, warn};

pub struct TracingLogger;

impl TracingLogger {
    pub fn new() -> Self {
        let _ = init_tracing();
        Self
    }
}

impl Logger for TracingLogger {
    fn info(&self, msg: &str) {
        info!(target: "clikit", "{}", msg);
    }

    fn debug(&self, msg: &str) {
        debug!(target: "clikit", "{}", msg);
    }

    fn warn(&self, msg: &str) {
        warn!(target: "clikit", "{}", msg);
    }

    fn error(&self, msg: &str) {
        error!(target: "clikit", "{}", msg);
    }
}

impl Default for TracingLogger {
    fn default() -> Self {
        Self::new()
    }
}

pub struct SimpleLogger {
    prefix: String,
}

impl SimpleLogger {
    pub fn new(prefix: &str) -> Self {
        Self {
            prefix: prefix.to_string(),
        }
    }
}

impl Logger for SimpleLogger {
    fn info(&self, msg: &str) {
        println!("[{} INFO] {}", self.prefix, msg);
    }

    fn debug(&self, msg: &str) {
        println!("[{} DEBUG] {}", self.prefix, msg);
    }

    fn warn(&self, msg: &str) {
        eprintln!("[{} WARN] {}", self.prefix, msg);
    }

    fn error(&self, msg: &str) {
        eprintln!("[{} ERROR] {}", self.prefix, msg);
    }
}
