//! RPC request handlers for phenotype-daemon
//! 
//! Optimized implementation with:
//! - DashMap for lock-free registry reads
//! - Buffer pooling for reduced allocations
//! - Direct response serialization to avoid double encoding
//! - Pre-allocated Vecs in list operations

use bytes::{BufMut, BytesMut};
use dashmap::DashMap;
use phenotype_skills::{DependencyResolver, Skill, SkillId, SkillRegistry};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{error, trace};

use crate::protocol::{Request, Response, VersionInfo};

/// Pooled buffer for encoding responses
pub struct BytesPool {
    pool: Vec<BytesMut>,
    max_size: usize,
}

impl BytesPool {
    pub fn new(max_size: usize) -> Self {
        Self {
            pool: Vec::with_capacity(max_size),
            max_size,
        }
    }

    #[inline]
    pub fn acquire(&mut self) -> BytesMut {
        self.pool
            .pop()
            .unwrap_or_else(|| BytesMut::with_capacity(4096))
    }

    #[inline]
    pub fn release(&mut self, mut buf: BytesMut) {
        if self.pool.len() < self.max_size {
            buf.clear();
            self.pool.push(buf);
        }
    }
}

/// Optimized shared state using DashMap for lock-free reads
#[derive(Clone)]
pub struct SharedState {
    /// Lock-free skill registry for read-heavy operations
    pub registry: Arc<DashMap<SkillId, Skill>>,
    /// Traditional registry for write operations (wrapped in RwLock)
    pub registry_lock: Arc<RwLock<SkillRegistry>>,
    /// Dependency resolver
    pub resolver: Arc<DependencyResolver>,
    /// Current version information
    pub version_info: VersionInfo,
    /// Bytes buffer pool
    pub buffer_pool: Arc<RwLock<BytesPool>>,
}

impl SharedState {
    pub fn new() -> Self {
        Self {
            registry: Arc::new(DashMap::new()),
            registry_lock: Arc::new(RwLock::new(SkillRegistry::new())),
            resolver: Arc::new(DependencyResolver::new()),
            version_info: VersionInfo::current(),
            buffer_pool: Arc::new(RwLock::new(BytesPool::new(32))),
        }
    }

    /// Get a buffer from the pool
    pub async fn acquire_buffer(&self) -> BytesMut {
        self.buffer_pool.write().await.acquire()
    }

    /// Return a buffer to the pool
    pub async fn release_buffer(&self, buf: BytesMut) {
        self.buffer_pool.write().await.release(buf);
    }

    /// Sync DashMap with the underlying registry
    pub async fn sync_registry(&self) {
        let reg = self.registry_lock.read().await;
        // Clear and rebuild DashMap from registry
        self.registry.clear();
        for skill in reg.list().iter() {
            self.registry.insert(SkillId::new(skill.id.to_string()), skill.clone());
        }
    }
}

/// RPC handler with optimized buffer pooling
pub struct RpcHandler {
    pub state: Arc<SharedState>,
    buffer_pool: BytesPool,
}

impl RpcHandler {
    pub fn new(state: Arc<SharedState>) -> Self {
        Self {
            state,
            buffer_pool: BytesPool::new(32),
        }
    }

    /// Handle a single request and return response
    pub async fn handle_request(&self, request: Request) -> Response {
        trace!("Handling request: {:?}", request);

        match request {
            Request::Ping => Response::Pong,

            Request::Version => Response::VersionInfo {
                version: self.state.version_info.version.clone(),
                protocol_version: self.state.version_info.protocol_version.clone(),
                features: self.state.version_info.features.clone(),
            },

            Request::Stats => {
                let registry_size = self.state.registry.len();
                Response::Stats {
                    total_skills: registry_size,
                    active_sandboxes: 0, // TODO: Implement sandbox tracking
                    buffer_pool_available: self.buffer_pool.pool.len(),
                    uptime_seconds: 0, // TODO: Track daemon start time
                }
            }

            Request::SkillList { limit, offset } => {
                let all_skills: Vec<Skill> = self.state.registry
                    .iter()
                    .map(|entry| entry.value().clone())
                    .collect();

                let total = all_skills.len();
                let start = offset.unwrap_or(0);
                let end = limit.map(|l| start + l).unwrap_or(total);
                let skills: Vec<Skill> = all_skills.into_iter().skip(start).take(end - start).collect();

                Response::SkillList { skills, total }
            }

            Request::SkillGet { id } => {
                let skill_id = SkillId::new(id);
                match self.state.registry.get(&skill_id) {
                    Some(entry) => Response::Skill { skill: entry.value().clone() },
                    None => Response::Error {
                        code: -32000,
                        message: format!("Skill not found: {}", skill_id),
                    },
                }
            }

            Request::SkillRegister { skill } => {
                let skill_id = SkillId::new(skill.id.to_string());
                
                // Insert into DashMap (lock-free)
                self.state.registry.insert(skill_id.clone(), skill.clone());
                
                // Also insert into underlying registry
                let reg = self.state.registry_lock.write().await;
                match reg.register(skill) {
                    Ok(_) => Response::Success,
                    Err(e) => Response::Error {
                        code: -32000,
                        message: format!("Failed to register skill: {}", e),
                    },
                }
            }

            Request::SkillUnregister { id } => {
                let skill_id = SkillId::new(id);
                
                // Remove from DashMap
                self.state.registry.remove(&skill_id);
                
                // Remove from underlying registry
                let reg = self.state.registry_lock.write().await;
                match reg.unregister(&skill_id) {
                    Ok(_) => Response::Success,
                    Err(e) => Response::Error {
                        code: -32000,
                        message: format!("Failed to unregister skill: {}", e),
                    },
                }
            }

            Request::SkillExists { id } => {
                let skill_id = SkillId::new(id);
                let exists = self.state.registry.contains_key(&skill_id);
                Response::SkillExists { exists }
            }

            Request::Resolve { skill_ids } => {
                let ids: Vec<SkillId> = skill_ids
                    .iter()
                    .map(|id| SkillId::new(id.clone()))
                    .collect();

                let mut resolved = Vec::with_capacity(ids.len());
                
                for id in ids {
                    if let Some(entry) = self.state.registry.get(&id) {
                        let skill = entry.value();
                        for dep in &skill.manifest.dependencies {
                            let dep_id = SkillId::new(dep.name.clone());
                            if self.state.registry.contains_key(&dep_id) {
                                resolved.push(dep_id.to_string());
                            }
                        }
                    }
                }

                Response::Resolved { skill_ids: resolved }
            }

            Request::CheckConflicts => {
                // Conflict checking logic
                let mut conflicts = Vec::new();
                let skills: Vec<_> = self.state.registry.iter().map(|e| e.value().clone()).collect();

                for skill in &skills {
                    for dep in &skill.manifest.dependencies {
                        let dep_id = SkillId::new(dep.name.clone());
                        if !self.state.registry.contains_key(&dep_id) {
                            conflicts.push(format!("Missing dependency: {} for skill {}", dep_id, skill.id));
                        }
                    }
                }

                Response::ConflictCheck { conflicts }
            }

            Request::CheckCircular { skill_ids } => {
                let ids: Vec<SkillId> = skill_ids
                    .iter()
                    .map(|id| SkillId::new(id.clone()))
                    .collect();

                // Simple circular dependency detection
                let has_cycle = check_circular_deps(&ids, &self.state.registry);

                Response::CircularCheck { has_cycle }
            }
        }
    }

    /// Handle an entire message stream with buffer reuse
    pub async fn handle_stream<S>(&mut self, mut stream: S) -> Result<(), Box<dyn std::error::Error + Send + Sync>>
    where
        S: tokio::io::AsyncReadExt + tokio::io::AsyncWriteExt + Unpin,
    {
        loop {
            // Acquire buffer for reading
            let mut read_buf = self.buffer_pool.acquire();
            
            // Read frame length (4 bytes, little-endian)
            let len_bytes = match stream.read_u32_le().await {
                Ok(len) => len as usize,
                Err(e) => {
                    if e.kind() == tokio::io::ErrorKind::UnexpectedEof {
                        return Ok(()); // Clean disconnect
                    }
                    return Err(Box::new(e));
                }
            };

            // Ensure buffer has capacity
            if read_buf.capacity() < len_bytes {
                read_buf.reserve(len_bytes - read_buf.capacity());
            }

            // Read message body
            let mut chunk = read_buf.split_to(len_bytes);
            stream.read_exact(&mut chunk).await?;

            // Parse request
            let request: Request = match rmp_serde::from_slice(&chunk) {
                Ok(req) => req,
                Err(e) => {
                    error!("Failed to parse request: {}", e);
                    
                    // Acquire buffer for error response
                    let mut err_buf = self.buffer_pool.acquire();
                    let response = Response::Error {
                        code: -32700,
                        message: format!("Parse error: {}", e),
                    };
                    
                    // Encode response
                    let err_payload = rmp_serde::to_vec_named(&response)?;
                    err_buf.put_u32_le(err_payload.len() as u32);
                    err_buf.put_slice(&err_payload);
                    
                    // Write and return buffer
                    stream.write_all(&err_buf).await?;
                    self.buffer_pool.release(err_buf);
                    continue;
                }
            };

            // Release read buffer back to pool
            self.buffer_pool.release(read_buf);

            // Handle request
            let response = self.handle_request(request).await;

            // Acquire buffer for response encoding
            let mut write_buf = self.buffer_pool.acquire();
            
            // Encode response with direct serialization
            let payload = rmp_serde::to_vec_named(&response)?;
            write_buf.put_u32_le(payload.len() as u32);
            write_buf.put_slice(&payload);

            // Send response
            stream.write_all(&write_buf).await?;
            
            // Return buffer to pool
            self.buffer_pool.release(write_buf);
        }
    }
}

/// Simple circular dependency detection
fn check_circular_deps(ids: &[SkillId], registry: &DashMap<SkillId, Skill>) -> bool {
    let mut visited = std::collections::HashSet::new();
    let mut stack = Vec::new();

    for id in ids {
        if has_cycle_from(id, registry, &mut visited, &mut stack) {
            return true;
        }
    }

    false
}

fn has_cycle_from(
    id: &SkillId,
    registry: &DashMap<SkillId, Skill>,
    visited: &mut std::collections::HashSet<SkillId>,
    stack: &mut Vec<SkillId>,
) -> bool {
    if stack.contains(id) {
        return true;
    }

    if visited.contains(id) {
        return false;
    }

    visited.insert(id.clone());
    stack.push(id.clone());

    if let Some(entry) = registry.get(id) {
        let skill = entry.value();
        for dep in &skill.manifest.dependencies {
            let dep_id = SkillId::new(dep.name.clone());
            if has_cycle_from(&dep_id, registry, visited, stack) {
                return true;
            }
        }
    }

    stack.pop();
    false
}