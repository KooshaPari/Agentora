//! Data deduplication and command locking for PhenoProc
//!
//! Provides:
//! - Generic deduplication filter using HashSet
//! - Bloom filter for probabilistic deduplication
//! - Command-level locking for preventing duplicate command execution
//!   (ported from thegent-sharecli Python implementation)

use anyhow::{bail, Result};
use std::collections::HashMap;
use std::collections::HashSet;
use std::hash::Hash;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

// ============================================================================
// Generic Deduplication
// ============================================================================

/// Deduplication filter using HashSet
#[derive(Debug, Default)]
pub struct DedupFilter<T: Hash + Eq> {
    seen: HashSet<T>,
}

impl<T: Hash + Eq> DedupFilter<T> {
    pub fn new() -> Self {
        Self {
            seen: HashSet::new(),
        }
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            seen: HashSet::with_capacity(capacity),
        }
    }

    pub fn check_and_insert(&mut self, item: T) -> bool {
        self.seen.insert(item)
    }

    pub fn clear(&mut self) {
        self.seen.clear();
    }

    pub fn len(&self) -> usize {
        self.seen.len()
    }

    pub fn is_empty(&self) -> bool {
        self.seen.is_empty()
    }
}

/// Bloom filter for probabilistic deduplication
pub struct BloomFilter {
    bits: Vec<bool>,
    size: usize,
    hash_count: usize,
}

impl BloomFilter {
    pub fn new(size: usize, hash_count: usize) -> Self {
        Self {
            bits: vec![false; size],
            size,
            hash_count,
        }
    }

    pub fn add(&mut self, item: &[u8]) {
        for i in 0..self.hash_count {
            let idx = self.hash(item, i) % self.size;
            self.bits[idx] = true;
        }
    }

    pub fn check(&self, item: &[u8]) -> bool {
        for i in 0..self.hash_count {
            let idx = self.hash(item, i) % self.size;
            if !self.bits[idx] {
                return false;
            }
        }
        true
    }

    pub fn check_and_add(&mut self, item: &[u8]) -> bool {
        let exists = self.check(item);
        if !exists {
            self.add(item);
        }
        exists
    }

    fn hash(&self, item: &[u8], seed: usize) -> usize {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        item.hash(&mut hasher);
        seed.hash(&mut hasher);
        hasher.finish() as usize
    }
}

// ============================================================================
// Command Deduplication (ported from thegent-sharecli)
// ============================================================================

/// Status of a command lock
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LockStatus {
    /// Lock is held by a process
    Locked,
    /// Lock has been released
    Released,
    /// Lock has expired
    Expired,
}

impl std::fmt::Display for LockStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LockStatus::Locked => write!(f, "locked"),
            LockStatus::Released => write!(f, "released"),
            LockStatus::Expired => write!(f, "expired"),
        }
    }
}

/// A lock representing a command execution
#[derive(Debug, Clone)]
pub struct CommandLock {
    /// Hash of the command being executed
    pub cmd_hash: String,
    /// Process ID holding the lock
    pub pid: u32,
    /// Optional output path for results
    pub output_path: Option<String>,
    /// Current lock status
    pub status: LockStatus,
    /// When the lock was acquired
    pub acquired_at: Instant,
    /// When the lock expires (if set)
    pub expires_at: Option<Instant>,
}

impl CommandLock {
    /// Create a new command lock
    pub fn new(cmd_hash: String, pid: u32, output_path: Option<String>) -> Self {
        Self {
            cmd_hash,
            pid,
            output_path,
            status: LockStatus::Locked,
            acquired_at: Instant::now(),
            expires_at: None,
        }
    }

    /// Set an expiration time for the lock
    pub fn with_expiry(mut self, duration: Duration) -> Self {
        self.expires_at = Some(Instant::now() + duration);
        self
    }

    /// Check if the lock is currently held
    pub fn is_locked(&self) -> bool {
        if self.status != LockStatus::Locked {
            return false;
        }

        if let Some(expires) = self.expires_at {
            if Instant::now() > expires {
                return false;
            }
        }

        true
    }

    /// Acquire the lock for a process
    pub fn acquire(&mut self, pid: u32, output_path: Option<String>) {
        self.pid = pid;
        self.output_path = output_path;
        self.status = LockStatus::Locked;
        self.acquired_at = Instant::now();
    }

    /// Release the lock
    pub fn release(&mut self, pid: u32) -> Result<()> {
        if self.pid != pid {
            bail!("Lock held by different process (PID: {})", self.pid);
        }

        self.status = LockStatus::Released;
        Ok(())
    }
}

/// In-memory lock adapter for command deduplication
#[derive(Debug, Clone)]
pub struct InMemoryLockAdapter {
    /// Internal lock storage
    locks: Arc<Mutex<HashMap<String, CommandLock>>>,
    /// Default lock expiration time
    default_ttl: Duration,
}

impl InMemoryLockAdapter {
    /// Create a new lock adapter with default TTL
    pub fn new() -> Self {
        Self::with_ttl(Duration::from_secs(300)) // 5 minutes default
    }

    /// Create a new lock adapter with custom TTL
    pub fn with_ttl(default_ttl: Duration) -> Self {
        Self {
            locks: Arc::new(Mutex::new(HashMap::new())),
            default_ttl,
        }
    }

    /// Acquire a lock for a command
    ///
    /// Returns the lock if acquired, or an error if already locked by another process
    pub fn acquire(
        &self,
        cmd_hash: &str,
        pid: u32,
        output_path: Option<String>,
    ) -> Result<CommandLock> {
        let mut locks = self.locks.lock().unwrap();

        if let Some(existing) = locks.get(cmd_hash) {
            // Check if lock is still valid
            if existing.is_locked() && existing.pid != pid {
                bail!(
                    "Command already locked by PID {} (acquired at {:?})",
                    existing.pid,
                    existing.acquired_at
                );
            }

            // Lock expired or released - can be reacquired
            let mut lock = existing.clone();
            lock.acquire(pid, output_path);
            locks.insert(cmd_hash.to_string(), lock.clone());
            Ok(lock)
        } else {
            // Create new lock
            let lock = CommandLock::new(cmd_hash.to_string(), pid, output_path)
                .with_expiry(self.default_ttl);
            locks.insert(cmd_hash.to_string(), lock.clone());
            Ok(lock)
        }
    }

    /// Release a lock for a command
    pub fn release(&self, cmd_hash: &str, pid: u32) -> Result<()> {
        let mut locks = self.locks.lock().unwrap();

        let lock = locks
            .get_mut(cmd_hash)
            .ok_or_else(|| anyhow::anyhow!("No lock found for command hash: {}", cmd_hash))?;

        lock.release(pid)
    }

    /// Get the current lock status for a command
    pub fn get(&self, cmd_hash: &str) -> Option<CommandLock> {
        let locks = self.locks.lock().unwrap();
        locks.get(cmd_hash).cloned()
    }

    /// List all active locks
    pub fn list_active(&self) -> Vec<CommandLock> {
        let locks = self.locks.lock().unwrap();
        locks.values().filter(|l| l.is_locked()).cloned().collect()
    }

    /// List all locks (including released/expired)
    pub fn list_all(&self) -> Vec<CommandLock> {
        let locks = self.locks.lock().unwrap();
        locks.values().cloned().collect()
    }

    /// Clean up expired locks
    pub fn cleanup_expired(&self) -> usize {
        let mut locks = self.locks.lock().unwrap();
        let before = locks.len();
        locks.retain(|_, lock| lock.is_locked());
        before - locks.len()
    }

    /// Clear all locks
    pub fn clear(&self) {
        let mut locks = self.locks.lock().unwrap();
        locks.clear();
    }
}

impl Default for InMemoryLockAdapter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dedup_filter() {
        let mut filter = DedupFilter::<i32>::new();
        assert!(filter.check_and_insert(1));
        assert!(!filter.check_and_insert(1)); // Already seen
        assert!(filter.check_and_insert(2));
        assert_eq!(filter.len(), 2);
    }

    #[test]
    fn test_bloom_filter() {
        let mut filter = BloomFilter::new(1000, 3);
        let item = b"test data";

        assert!(!filter.check(item)); // Should be false initially
        filter.add(item);
        assert!(filter.check(item)); // Should be true after adding
    }

    #[test]
    fn test_lock_acquire_and_release() {
        let adapter = InMemoryLockAdapter::new();

        // Acquire lock
        let lock = adapter.acquire("cmd123", 1234, None).unwrap();
        assert_eq!(lock.cmd_hash, "cmd123");
        assert_eq!(lock.pid, 1234);
        assert!(lock.is_locked());

        // Release lock
        adapter.release("cmd123", 1234).unwrap();

        // Verify released
        let lock = adapter.get("cmd123").unwrap();
        assert!(!lock.is_locked());
    }

    #[test]
    fn test_duplicate_lock_prevention() {
        let adapter = InMemoryLockAdapter::new();

        // First process acquires
        adapter.acquire("cmd123", 1000, None).unwrap();

        // Second process should fail
        let result = adapter.acquire("cmd123", 2000, None);
        assert!(result.is_err());
    }

    #[test]
    fn test_same_process_can_reacquire() {
        let adapter = InMemoryLockAdapter::new();

        // Acquire and release
        adapter.acquire("cmd123", 1000, None).unwrap();
        adapter.release("cmd123", 1000).unwrap();

        // Same process can acquire again
        let result = adapter.acquire("cmd123", 1000, None);
        assert!(result.is_ok());
    }

    #[test]
    fn test_list_active() {
        let adapter = InMemoryLockAdapter::new();

        adapter.acquire("cmd1", 1000, None).unwrap();
        adapter.acquire("cmd2", 1001, None).unwrap();

        let active = adapter.list_active();
        assert_eq!(active.len(), 2);
    }
}
