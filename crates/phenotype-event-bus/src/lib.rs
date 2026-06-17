//! Phenotype event bus library

pub struct EventBus;

impl EventBus {
    pub fn new() -> Self {
        Self
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new()
    }
}
