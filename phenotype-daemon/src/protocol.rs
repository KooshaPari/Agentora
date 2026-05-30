//! Protocol definitions for phenotype-daemon RPC

use std::sync::Arc;

use dashmap::DashMap;
use phenotype_skills::Skill;
use serde::{Deserialize, Serialize};
use bytes::BytesMut;

/// Buffer pool for zero-allocation message handling
pub struct BufferPool {
    pool: Arc<dashmap::DashMap<u64, Vec<BytesMut>>>,
}

impl BufferPool {
    /// Create a new buffer pool with pre-allocated buffers
    pub fn new(buffer_count: usize, buffer_size: usize) -> Self {
        let pool = Arc::new(DashMap::new());

        // Pre-allocate buffers for each thread
        for thread_id in 0..4u64 {
            let mut buffers = Vec::with_capacity(buffer_count / 4);
            for _ in 0..(buffer_count / 4) {
                buffers.push(BytesMut::with_capacity(buffer_size));
            }
            pool.insert(thread_id, buffers);
        }

        Self { pool }
    }

    /// Get a buffer from the pool
    pub fn acquire(&self, thread_id: u64) -> Option<BytesMut> {
        self.pool
            .get_mut(&thread_id)
            .and_then(|mut entry| entry.pop())
    }

    /// Return a buffer to the pool
    pub fn release(&self, thread_id: u64, mut buffer: BytesMut) {
        buffer.clear();
        if let Some(mut entry) = self.pool.get_mut(&thread_id) {
            if entry.len() < 64 { // Max 64 buffers per thread
                entry.push(buffer);
            }
        }
    }
}

/// Connection stats for monitoring
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ConnectionStats {
    /// Total requests processed
    pub requests_processed: u64,
    /// Total bytes received
    pub bytes_received: u64,
    /// Total bytes sent
    pub bytes_sent: u64,
    /// Average response time in microseconds
    pub avg_response_time_us: u64,
    /// Active connections
    pub active_connections: u32,
}

/// Request types for RPC protocol
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "method", content = "params")]
pub enum Request {
    /// Health check
    #[serde(rename = "ping")]
    Ping,
    /// Get version information
    #[serde(rename = "version")]
    Version,
    /// Get daemon statistics
    #[serde(rename = "stats")]
    Stats,

    /// List all registered skills with pagination
    #[serde(rename = "skill.list")]
    SkillList { limit: Option<usize>, offset: Option<usize> },
    /// Get a skill by ID
    #[serde(rename = "skill.get")]
    SkillGet { id: String },
    /// Register a skill
    #[serde(rename = "skill.register")]
    SkillRegister { skill: Skill },
    /// Unregister a skill
    #[serde(rename = "skill.unregister")]
    SkillUnregister { id: String },
    /// Check if a skill exists
    #[serde(rename = "skill.exists")]
    SkillExists { id: String },

    /// Resolve dependencies for skills
    #[serde(rename = "resolve")]
    Resolve { skill_ids: Vec<String> },
    /// Check for circular dependencies
    #[serde(rename = "check_circular")]
    CheckCircular { skill_ids: Vec<String> },
    /// Check for conflicts/missing dependencies
    #[serde(rename = "check_conflicts")]
    CheckConflicts,
}

/// Response types for RPC protocol
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Response {
    /// Success response
    Success,
    /// Error response
    Error {
        code: i32,
        message: String,
    },
    /// Pong response for ping
    Pong,
    /// Version information
    VersionInfo {
        version: String,
        protocol_version: String,
        features: Vec<String>,
    },
    /// Daemon statistics
    Stats {
        total_skills: usize,
        active_sandboxes: usize,
        buffer_pool_available: usize,
        uptime_seconds: u64,
    },
    /// Skill list response
    SkillList {
        skills: Vec<Skill>,
        total: usize,
    },
    /// Single skill response
    Skill {
        skill: Skill,
    },
    /// Skill exists check
    SkillExists {
        exists: bool,
    },
    /// Dependency resolution result
    Resolved {
        skill_ids: Vec<String>,
    },
    /// Conflict check result
    ConflictCheck {
        conflicts: Vec<String>,
    },
    /// Circular dependency check result
    CircularCheck {
        has_cycle: bool,
    },
}

/// Version information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionInfo {
    /// Daemon version
    pub version: String,
    /// Protocol version
    pub protocol_version: String,
    /// Supported features
    pub features: Vec<String>,
}

impl VersionInfo {
    /// Get current version info
    pub fn current() -> Self {
        Self {
            version: env!("CARGO_PKG_VERSION").to_string(),
            protocol_version: "1.0".to_string(),
            features: vec![
                "unix-socket".to_string(),
                "tcp".to_string(),
                "jsonrpc".to_string(),
                #[cfg(feature = "nats-cluster")]
                "nats-cluster".to_string(),
            ],
        }
    }
}

/// Default socket path for Unix domain sockets
pub const DEFAULT_SOCKET_PATH: &str = "/tmp/phenotype-daemon.sock";

/// Default TCP port
pub const DEFAULT_TCP_PORT: u16 = 8953;