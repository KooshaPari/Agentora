//! Memory domain - Short and long term memory

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

/// Memory entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub role: MemoryRole,
    pub content: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub metadata: serde_json::Value,
}

impl MemoryEntry {
    pub fn user(content: impl Into<String>) -> Self {
        Self {
            role: MemoryRole::User,
            content: content.into(),
            timestamp: chrono::Utc::now(),
            metadata: serde_json::json!({}),
        }
    }

    pub fn assistant(content: impl Into<String>) -> Self {
        Self {
            role: MemoryRole::Assistant,
            content: content.into(),
            timestamp: chrono::Utc::now(),
            metadata: serde_json::json!({}),
        }
    }

    pub fn system(content: impl Into<String>) -> Self {
        Self {
            role: MemoryRole::System,
            content: content.into(),
            timestamp: chrono::Utc::now(),
            metadata: serde_json::json!({}),
        }
    }
}

/// Memory role
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MemoryRole {
    System,
    User,
    Assistant,
    Tool,
}

/// Short-term memory - conversation context
pub struct ShortTermMemory {
    entries: VecDeque<MemoryEntry>,
    limit: usize,
}

impl ShortTermMemory {
    pub fn new(limit: usize) -> Self {
        Self {
            entries: VecDeque::new(),
            limit,
        }
    }

    pub fn add(&mut self, entry: MemoryEntry) {
        if self.entries.len() >= self.limit {
            self.entries.pop_front();
        }
        self.entries.push_back(entry);
    }

    pub fn entries(&self) -> Vec<&MemoryEntry> {
        self.entries.iter().collect()
    }

    pub fn clear(&mut self) {
        self.entries.clear();
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

impl Default for ShortTermMemory {
    fn default() -> Self {
        Self::new(10)
    }
}

/// Memory store trait - for long-term memory
pub trait MemoryStore: Send + Sync {
    /// Save a memory entry
    fn save(&mut self, entry: &MemoryEntry) -> Result<(), String>;

    /// Search memories
    fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, String>;

    /// Clear all memories
    fn clear(&mut self) -> Result<(), String>;
}

/// In-memory store (for testing)
pub struct InMemoryStore {
    entries: Vec<MemoryEntry>,
}

impl InMemoryStore {
    pub fn new() -> Self {
        Self {
            entries: Vec::new(),
        }
    }
}

impl Default for InMemoryStore {
    fn default() -> Self {
        Self::new()
    }
}

impl MemoryStore for InMemoryStore {
    fn save(&mut self, entry: &MemoryEntry) -> Result<(), String> {
        self.entries.push(entry.clone());
        Ok(())
    }

    fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, String> {
        let results: Vec<_> = self.entries
            .iter()
            .filter(|e| e.content.contains(query))
            .take(limit)
            .cloned()
            .collect();
        Ok(results)
    }

    fn clear(&mut self) -> Result<(), String> {
        self.entries.clear();
        Ok(())
    }
}

/// Long-term memory
pub struct LongTermMemory<S: MemoryStore> {
    store: S,
}

impl<S: MemoryStore> LongTermMemory<S> {
    pub fn new(store: S) -> Self {
        Self { store }
    }

    pub fn add(&mut self, entry: MemoryEntry) -> Result<(), String> {
        self.store.save(&entry)
    }

    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, String> {
        self.store.search(query, limit)
    }

    pub fn clear(&mut self) -> Result<(), String> {
        self.store.clear()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_short_term_memory() {
        let mut memory = ShortTermMemory::new(2);

        memory.add(MemoryEntry::user("Hello"));
        memory.add(MemoryEntry::assistant("Hi there!"));
        memory.add(MemoryEntry::user("How are you?")); // Should evict first

        assert_eq!(memory.len(), 2);
    }
}
