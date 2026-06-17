//! Priority-based task queue system for PhenoProc
//!
//! Provides ordered task execution with priority levels for
//! multi-agent coordination and resource management.
//!
//! Ported from thegent-sharecli Python implementation.

use anyhow::Result;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::Instant;
use uuid::Uuid;

/// Task priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Priority {
    /// Critical - immediate execution
    Critical = 0,
    /// High - execute after critical
    High = 1,
    /// Normal - default priority
    Normal = 2,
    /// Low - execute when resources available
    Low = 3,
}

impl std::str::FromStr for Priority {
    type Err = ();
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "critical" => Ok(Priority::Critical),
            "high" => Ok(Priority::High),
            "normal" => Ok(Priority::Normal),
            "low" => Ok(Priority::Low),
            _ => Err(()),
        }
    }
}

impl std::fmt::Display for Priority {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Priority::Critical => write!(f, "critical"),
            Priority::High => write!(f, "high"),
            Priority::Normal => write!(f, "normal"),
            Priority::Low => write!(f, "low"),
        }
    }
}

/// Status of a queue item
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QueueStatus {
    /// Item is waiting in queue
    Queued,
    /// Item is being processed
    Processing,
    /// Item completed successfully
    Completed,
    /// Item failed
    Failed,
    /// Item was dequeued
    Dequeued,
}

impl std::fmt::Display for QueueStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            QueueStatus::Queued => write!(f, "queued"),
            QueueStatus::Processing => write!(f, "processing"),
            QueueStatus::Completed => write!(f, "completed"),
            QueueStatus::Failed => write!(f, "failed"),
            QueueStatus::Dequeued => write!(f, "dequeued"),
        }
    }
}

/// An item in the task queue
#[derive(Debug, Clone)]
pub struct QueueItem {
    /// Unique identifier
    pub id: String,
    /// Command to execute
    pub command: String,
    /// Current status
    pub status: QueueStatus,
    /// Priority level
    pub priority: Priority,
    /// When item was added to queue
    pub created_at: Instant,
    /// When processing started (if applicable)
    pub started_at: Option<Instant>,
    /// When processing completed (if applicable)
    pub completed_at: Option<Instant>,
    /// Optional metadata
    pub metadata: Option<serde_json::Value>,
}

impl QueueItem {
    /// Create a new queue item
    pub fn new(command: String, priority: Priority) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            command,
            status: QueueStatus::Queued,
            priority,
            created_at: Instant::now(),
            started_at: None,
            completed_at: None,
            metadata: None,
        }
    }

    /// Mark item as processing
    pub fn start(&mut self) {
        self.status = QueueStatus::Processing;
        self.started_at = Some(Instant::now());
    }

    /// Mark item as completed
    pub fn complete(&mut self) {
        self.status = QueueStatus::Completed;
        self.completed_at = Some(Instant::now());
    }

    /// Mark item as failed
    pub fn fail(&mut self) {
        self.status = QueueStatus::Failed;
        self.completed_at = Some(Instant::now());
    }

    /// Get processing duration (if completed)
    pub fn duration(&self) -> Option<std::time::Duration> {
        match (self.started_at, self.completed_at) {
            (Some(start), Some(end)) => Some(end - start),
            _ => None,
        }
    }

    /// Get wait time before processing
    pub fn wait_time(&self) -> Option<std::time::Duration> {
        self.started_at.map(|start| start - self.created_at)
    }
}

/// In-memory queue adapter for task management
#[derive(Debug)]
pub struct InMemoryQueueAdapter {
    /// Internal queue storage (sorted by priority)
    queue: Arc<Mutex<VecDeque<QueueItem>>>,
    /// Items by ID for lookup
    items: Arc<Mutex<std::collections::HashMap<String, QueueItem>>>,
}

impl InMemoryQueueAdapter {
    /// Create a new queue adapter
    pub fn new() -> Self {
        Self {
            queue: Arc::new(Mutex::new(VecDeque::new())),
            items: Arc::new(Mutex::new(std::collections::HashMap::new())),
        }
    }

    /// Add an item to the queue
    pub fn enqueue(
        &self,
        command: String,
        priority: Priority,
        metadata: Option<serde_json::Value>,
    ) -> QueueItem {
        let mut item = QueueItem::new(command, priority);
        item.metadata = metadata;

        let mut queue = self.queue.lock().unwrap();
        let mut items = self.items.lock().unwrap();

        // Insert in priority order
        let insert_pos = queue
            .iter()
            .position(|i| i.priority > priority)
            .unwrap_or(queue.len());

        queue.insert(insert_pos, item.clone());
        items.insert(item.id.clone(), item.clone());

        item
    }

    /// Remove and return the next item (highest priority, FIFO within same priority)
    pub fn dequeue(&self) -> Option<QueueItem> {
        let mut queue = self.queue.lock().unwrap();
        let mut items = self.items.lock().unwrap();

        queue.pop_front().map(|mut item| {
            item.status = QueueStatus::Dequeued;
            items.insert(item.id.clone(), item.clone());
            item
        })
    }

    /// View the next item without removing it
    pub fn peek(&self) -> Option<QueueItem> {
        let queue = self.queue.lock().unwrap();
        queue.front().cloned()
    }

    /// Get current queue length
    pub fn length(&self) -> usize {
        let queue = self.queue.lock().unwrap();
        queue.len()
    }

    /// Check if queue is empty
    pub fn is_empty(&self) -> bool {
        self.length() == 0
    }

    /// Get an item by ID
    pub fn get(&self, id: &str) -> Option<QueueItem> {
        let items = self.items.lock().unwrap();
        items.get(id).cloned()
    }

    /// Update item status
    pub fn update_status(&self, id: &str, status: QueueStatus) -> Result<()> {
        let mut items = self.items.lock().unwrap();

        let item = items
            .get_mut(id)
            .ok_or_else(|| anyhow::anyhow!("Item not found: {}", id))?;

        item.status = status;

        match status {
            QueueStatus::Processing => item.started_at = Some(Instant::now()),
            QueueStatus::Completed | QueueStatus::Failed => {
                item.completed_at = Some(Instant::now())
            }
            _ => {}
        }

        Ok(())
    }

    /// List all queued items (not yet processed)
    pub fn list_queued(&self) -> Vec<QueueItem> {
        let queue = self.queue.lock().unwrap();
        queue.iter().cloned().collect()
    }

    /// List all items (including processed)
    pub fn list_all(&self) -> Vec<QueueItem> {
        let items = self.items.lock().unwrap();
        items.values().cloned().collect()
    }

    /// List items by status
    pub fn list_by_status(&self, status: QueueStatus) -> Vec<QueueItem> {
        let items = self.items.lock().unwrap();
        items
            .values()
            .filter(|i| i.status == status)
            .cloned()
            .collect()
    }

    /// Clear the entire queue
    pub fn clear(&self) {
        let mut queue = self.queue.lock().unwrap();
        let mut items = self.items.lock().unwrap();
        queue.clear();
        items.clear();
    }

    /// Remove completed/failed items from history
    pub fn cleanup_completed(&self) -> usize {
        let mut items = self.items.lock().unwrap();
        let before = items.len();
        items.retain(|_, item| {
            item.status != QueueStatus::Completed && item.status != QueueStatus::Failed
        });
        before - items.len()
    }

    /// Get queue statistics
    pub fn stats(&self) -> QueueStats {
        let items = self.items.lock().unwrap();
        let queued = items
            .values()
            .filter(|i| i.status == QueueStatus::Queued)
            .count();
        let processing = items
            .values()
            .filter(|i| i.status == QueueStatus::Processing)
            .count();
        let completed = items
            .values()
            .filter(|i| i.status == QueueStatus::Completed)
            .count();
        let failed = items
            .values()
            .filter(|i| i.status == QueueStatus::Failed)
            .count();

        QueueStats {
            queued,
            processing,
            completed,
            failed,
            total: items.len(),
        }
    }
}

impl Default for InMemoryQueueAdapter {
    fn default() -> Self {
        Self::new()
    }
}

/// Queue statistics
#[derive(Debug, Clone)]
pub struct QueueStats {
    /// Number of items waiting
    pub queued: usize,
    /// Number of items being processed
    pub processing: usize,
    /// Number of completed items
    pub completed: usize,
    /// Number of failed items
    pub failed: usize,
    /// Total number of items tracked
    pub total: usize,
}

impl std::fmt::Display for QueueStats {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "QueueStats {{ queued: {}, processing: {}, completed: {}, failed: {}, total: {} }}",
            self.queued, self.processing, self.completed, self.failed, self.total
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_enqueue_dequeue() {
        let queue = InMemoryQueueAdapter::new();

        let _item1 = queue.enqueue("cmd1".to_string(), Priority::Normal, None);
        let _item2 = queue.enqueue("cmd2".to_string(), Priority::High, None);

        assert_eq!(queue.length(), 2);

        // High priority should come first
        let next = queue.dequeue().unwrap();
        assert_eq!(next.command, "cmd2");
        assert_eq!(next.priority, Priority::High);

        let next = queue.dequeue().unwrap();
        assert_eq!(next.command, "cmd1");
    }

    #[test]
    fn test_priority_ordering() {
        let queue = InMemoryQueueAdapter::new();

        queue.enqueue("low".to_string(), Priority::Low, None);
        queue.enqueue("critical".to_string(), Priority::Critical, None);
        queue.enqueue("normal".to_string(), Priority::Normal, None);
        queue.enqueue("high".to_string(), Priority::High, None);

        let next = queue.dequeue().unwrap();
        assert_eq!(next.priority, Priority::Critical);

        let next = queue.dequeue().unwrap();
        assert_eq!(next.priority, Priority::High);

        let next = queue.dequeue().unwrap();
        assert_eq!(next.priority, Priority::Normal);

        let next = queue.dequeue().unwrap();
        assert_eq!(next.priority, Priority::Low);
    }

    #[test]
    fn test_update_status() {
        let queue = InMemoryQueueAdapter::new();
        let item = queue.enqueue("cmd".to_string(), Priority::Normal, None);

        queue
            .update_status(&item.id, QueueStatus::Processing)
            .unwrap();

        let updated = queue.get(&item.id).unwrap();
        assert_eq!(updated.status, QueueStatus::Processing);
        assert!(updated.started_at.is_some());
    }

    #[test]
    fn test_stats() {
        let queue = InMemoryQueueAdapter::new();

        queue.enqueue("cmd1".to_string(), Priority::Normal, None);
        queue.enqueue("cmd2".to_string(), Priority::Normal, None);

        let item3 = queue.enqueue("cmd3".to_string(), Priority::Normal, None);
        queue
            .update_status(&item3.id, QueueStatus::Completed)
            .unwrap();

        let stats = queue.stats();
        assert_eq!(stats.queued, 2);
        assert_eq!(stats.completed, 1);
        assert_eq!(stats.total, 3);
    }

    #[test]
    fn test_peek() {
        let queue = InMemoryQueueAdapter::new();
        queue.enqueue("cmd".to_string(), Priority::High, None);

        let peeked = queue.peek().unwrap();
        assert_eq!(peeked.command, "cmd");
        assert_eq!(queue.length(), 1); // Item still in queue
    }
}
