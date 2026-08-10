//! Memory adapters - Implementations of [`MemoryPort`].
//!
//! * [`InMemoryAdapter`] - thread-safe wrapper around [`InMemoryStore`].
//!   No external deps, suitable for tests and embedded use.
//! * [`RedisMemoryAdapter`] - Redis-backed store. Activated by the
//!   `redis-memory` cargo feature.
//! * [`SqliteMemoryAdapter`] - SQLite-backed store. Activated by the
//!   `sqlite-memory` cargo feature.

use async_trait::async_trait;
use std::sync::Mutex;

use crate::domain::memory::{InMemoryStore, MemoryEntry, MemoryStore};
use crate::domain::ports::MemoryPort;
use crate::domain::Result;

/// Thread-safe in-memory adapter. Cheap and dependency-free.
#[derive(Debug, Default)]
pub struct InMemoryAdapter {
    inner: Mutex<InMemoryStore>,
}

impl InMemoryAdapter {
    /// Build a fresh, empty adapter.
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(InMemoryStore::new()),
        }
    }
}

#[async_trait]
impl MemoryPort for InMemoryAdapter {
    fn add(&self, entry: MemoryEntry) -> Result<()> {
        let mut store = self
            .inner
            .lock()
            .map_err(|e| crate::domain::Error::Memory(format!("lock poisoned: {e}")))?;
        store.save(&entry).map_err(crate::domain::Error::Memory)
    }

    fn recent(&self, limit: usize) -> Result<Vec<MemoryEntry>> {
        let store = self
            .inner
            .lock()
            .map_err(|e| crate::domain::Error::Memory(format!("lock poisoned: {e}")))?;
        let mut all = store
            .search("", usize::MAX)
            .map_err(crate::domain::Error::Memory)?;
        drop(store);
        all.reverse();
        all.truncate(limit);
        Ok(all)
    }

    fn search(&self, query: &str) -> Result<Vec<MemoryEntry>> {
        let store = self
            .inner
            .lock()
            .map_err(|e| crate::domain::Error::Memory(format!("lock poisoned: {e}")))?;
        store
            .search(query, usize::MAX)
            .map_err(crate::domain::Error::Memory)
    }
}

/// Redis-backed memory adapter. Stores each entry as JSON under a
/// namespaced key; supports prefix-based enumeration.
#[cfg(feature = "redis-memory")]
#[derive(Debug, Clone)]
pub struct RedisMemoryAdapter {
    client: redis::Client,
    namespace: String,
}

#[cfg(feature = "redis-memory")]
impl RedisMemoryAdapter {
    /// Connect to a Redis instance by URL (`redis://host:port/db`).
    pub fn connect(url: &str, namespace: impl Into<String>) -> Result<Self> {
        let client = redis::Client::open(url)
            .map_err(|e| crate::domain::Error::Memory(format!("redis: {e}")))?;
        Ok(Self {
            client,
            namespace: namespace.into(),
        })
    }

    fn key(&self, id: &str) -> String {
        format!("{}:{}", self.namespace, id)
    }
}

#[cfg(feature = "redis-memory")]
#[async_trait]
impl MemoryPort for RedisMemoryAdapter {
    fn add(&self, entry: MemoryEntry) -> Result<()> {
        let client = self.client.clone();
        let key = self.key(&entry.timestamp.to_rfc3339());
        let value = serde_json::to_string(&entry)
            .map_err(|e| crate::domain::Error::Memory(format!("encode: {e}")))?;
        let mut conn = client
            .get_connection()
            .map_err(|e| crate::domain::Error::Memory(format!("redis: {e}")))?;
        redis::cmd("SET")
            .arg(&key)
            .arg(&value)
            .query::<()>(&mut conn)
            .map_err(|e| crate::domain::Error::Memory(format!("redis SET: {e}")))?;
        Ok(())
    }

    fn recent(&self, limit: usize) -> Result<Vec<MemoryEntry>> {
        let pattern = format!("{}:*", self.namespace);
        let client = self.client.clone();
        let mut conn = client
            .get_connection()
            .map_err(|e| crate::domain::Error::Memory(format!("redis: {e}")))?;
        let mut keys: Vec<String> = redis::cmd("KEYS")
            .arg(&pattern)
            .query(&mut conn)
            .map_err(|e| crate::domain::Error::Memory(format!("redis KEYS: {e}")))?;
        keys.sort_by(|a, b| b.cmp(a));
        keys.truncate(limit);
        let mut out = Vec::with_capacity(keys.len());
        for k in keys {
            let raw: Option<String> = redis::cmd("GET")
                .arg(&k)
                .query(&mut conn)
                .map_err(|e| crate::domain::Error::Memory(format!("redis GET: {e}")))?;
            if let Some(s) = raw {
                let entry: MemoryEntry = serde_json::from_str(&s)
                    .map_err(|e| crate::domain::Error::Memory(format!("decode: {e}")))?;
                out.push(entry);
            }
        }
        Ok(out)
    }

    fn search(&self, query: &str) -> Result<Vec<MemoryEntry>> {
        let all = self.recent(usize::MAX)?;
        Ok(all
            .into_iter()
            .filter(|e| e.content.contains(query))
            .collect())
    }
}

/// SQLite-backed memory adapter. Stores all entries in a single `memories`
/// table indexed by timestamp; uses `LIKE` for search.
#[cfg(feature = "sqlite-memory")]
pub struct SqliteMemoryAdapter {
    conn: Mutex<rusqlite::Connection>,
}

#[cfg(feature = "sqlite-memory")]
impl SqliteMemoryAdapter {
    /// Open (or create) a SQLite file and ensure the schema is present.
    pub fn open(path: &str) -> Result<Self> {
        let conn = rusqlite::Connection::open(path)
            .map_err(|e| crate::domain::Error::Memory(format!("sqlite: {e}")))?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL
             );
             CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories(ts);",
        )
        .map_err(|e| crate::domain::Error::Memory(format!("sqlite init: {e}")))?;
        Ok(Self {
            conn: Mutex::new(conn),
        })
    }
}

#[cfg(feature = "sqlite-memory")]
fn parse_role(s: &str) -> crate::domain::memory::MemoryRole {
    use crate::domain::memory::MemoryRole;
    match s {
        "User" => MemoryRole::User,
        "Assistant" => MemoryRole::Assistant,
        "System" => MemoryRole::System,
        _ => MemoryRole::Tool,
    }
}

#[cfg(feature = "sqlite-memory")]
fn row_to_entry(ts: String, role_s: String, content: String, metadata_s: String) -> MemoryEntry {
    let role = parse_role(&role_s);
    let metadata: serde_json::Value =
        serde_json::from_str(&metadata_s).unwrap_or(serde_json::json!({}));
    let timestamp = chrono::DateTime::parse_from_rfc3339(&ts)
        .map(|d| d.with_timezone(&chrono::Utc))
        .unwrap_or_else(|_| chrono::Utc::now());
    MemoryEntry {
        role,
        content,
        timestamp,
        metadata,
    }
}

#[cfg(feature = "sqlite-memory")]
#[async_trait]
impl MemoryPort for SqliteMemoryAdapter {
    fn add(&self, entry: MemoryEntry) -> Result<()> {
        let conn = self
            .conn
            .lock()
            .map_err(|e| crate::domain::Error::Memory(format!("lock poisoned: {e}")))?;
        conn.execute(
            "INSERT INTO memories (ts, role, content, metadata) VALUES (?1, ?2, ?3, ?4)",
            rusqlite::params![
                entry.timestamp.to_rfc3339(),
                format!("{:?}", entry.role),
                entry.content,
                serde_json::to_string(&entry.metadata).unwrap_or_else(|_| "{}".to_string()),
            ],
        )
        .map_err(|e| crate::domain::Error::Memory(format!("sqlite insert: {e}")))?;
        Ok(())
    }

    fn recent(&self, limit: usize) -> Result<Vec<MemoryEntry>> {
        let conn = self
            .conn
            .lock()
            .map_err(|e| crate::domain::Error::Memory(format!("lock poisoned: {e}")))?;
        let mut stmt = conn
            .prepare("SELECT ts, role, content, metadata FROM memories ORDER BY ts DESC LIMIT ?1")
            .map_err(|e| crate::domain::Error::Memory(format!("sqlite prepare: {e}")))?;
        let rows = stmt
            .query_map(rusqlite::params![limit as i64], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                ))
            })
            .map_err(|e| crate::domain::Error::Memory(format!("sqlite query: {e}")))?;
        rows.into_iter()
            .map(|r| {
                let (ts, role, content, metadata) =
                    r.map_err(|e| crate::domain::Error::Memory(format!("sqlite row: {e}")))?;
                Ok(row_to_entry(ts, role, content, metadata))
            })
            .collect()
    }

    fn search(&self, query: &str) -> Result<Vec<MemoryEntry>> {
        let conn = self
            .conn
            .lock()
            .map_err(|e| crate::domain::Error::Memory(format!("lock poisoned: {e}")))?;
        let mut stmt = conn
            .prepare(
                "SELECT ts, role, content, metadata FROM memories \
                 WHERE content LIKE ?1 ORDER BY ts DESC",
            )
            .map_err(|e| crate::domain::Error::Memory(format!("sqlite prepare: {e}")))?;
        let pattern = format!("%{query}%");
        let rows = stmt
            .query_map(rusqlite::params![pattern], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                ))
            })
            .map_err(|e| crate::domain::Error::Memory(format!("sqlite query: {e}")))?;
        rows.into_iter()
            .map(|r| {
                let (ts, role, content, metadata) =
                    r.map_err(|e| crate::domain::Error::Memory(format!("sqlite row: {e}")))?;
                Ok(row_to_entry(ts, role, content, metadata))
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::memory::{MemoryEntry, MemoryRole};

    #[test]
    fn in_memory_adapter_add_and_recent() {
        let m = InMemoryAdapter::new();
        m.add(MemoryEntry {
            role: MemoryRole::User,
            content: "first".into(),
            timestamp: chrono::Utc::now(),
            metadata: serde_json::json!({}),
        })
        .unwrap();
        m.add(MemoryEntry {
            role: MemoryRole::User,
            content: "second".into(),
            timestamp: chrono::Utc::now(),
            metadata: serde_json::json!({}),
        })
        .unwrap();
        let recent = m.recent(10).unwrap();
        assert_eq!(recent.len(), 2);
        assert_eq!(recent[0].content, "second");
        assert_eq!(recent[1].content, "first");
    }

    #[test]
    fn in_memory_adapter_search() {
        let m = InMemoryAdapter::new();
        m.add(MemoryEntry {
            role: MemoryRole::User,
            content: "the quick brown fox".into(),
            timestamp: chrono::Utc::now(),
            metadata: serde_json::json!({}),
        })
        .unwrap();
        m.add(MemoryEntry {
            role: MemoryRole::User,
            content: "lazy dog".into(),
            timestamp: chrono::Utc::now(),
            metadata: serde_json::json!({}),
        })
        .unwrap();
        let hits = m.search("fox").unwrap();
        assert_eq!(hits.len(), 1);
        assert!(hits[0].content.contains("fox"));
    }
}
