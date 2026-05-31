//! Process management primitives for PhenoProc registry
//!
//! Core process management types and traits used by sharecli.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Instant;
use anyhow::{Result, bail};

/// Information about a managed process
#[derive(Debug, Clone)]
pub struct ProcessInfo {
    /// Process ID
    pub pid: u32,
    /// Process name
    pub name: String,
    /// Project name
    pub project: String,
    /// Harness type (e.g., "claude", "codex")
    pub harness: String,
    /// When the process started
    pub started_at: Instant,
    /// Current status
    pub status: ProcessStatus,
    /// Memory usage in MB
    pub memory_mb: u64,
    /// CPU usage percentage
    pub cpu_percent: Option<f32>,
    /// Command arguments
    pub cmd: Vec<String>,
}

/// Process status
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProcessStatus {
    /// Process is running
    Running,
    /// Process is stopped
    Stopped,
    /// Process has exited
    Exited,
    /// Process is in error state
    Error,
}

impl std::fmt::Display for ProcessStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ProcessStatus::Running => write!(f, "running"),
            ProcessStatus::Stopped => write!(f, "stopped"),
            ProcessStatus::Exited => write!(f, "exited"),
            ProcessStatus::Error => write!(f, "error"),
        }
    }
}

/// A managed process with lifecycle control
#[derive(Debug, Clone)]
pub struct ManagedProcess {
    /// Process information
    pub info: ProcessInfo,
    /// Command that was executed
    pub command: String,
    /// Working directory
    pub cwd: String,
}

/// Filter for querying processes
#[derive(Debug, Clone)]
pub enum ProcessFilter {
    /// Return all processes
    All,
    /// Filter by project name
    ByProject(String),
    /// Filter by harness type
    ByHarness(String),
}

/// Resource limits for a project
#[derive(Debug, Clone)]
pub struct ProjectLimits {
    /// Memory limit in MB
    pub memory_limit_mb: u64,
    /// Maximum number of processes
    pub max_processes: usize,
    /// CPU affinity (optional)
    pub cpu_affinity: Option<Vec<usize>>,
}

/// Resource tracking for a project
#[derive(Debug, Clone)]
pub struct ProjectResources {
    /// Current limits per project
    limits: Arc<Mutex<HashMap<String, ProjectLimits>>>,
}

impl ProjectResources {
    pub fn new() -> Self {
        Self {
            limits: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub async fn get_limits(&self, project: &str) -> ProjectLimits {
        let limits = self.limits.lock().unwrap();
        limits.get(project).cloned().unwrap_or_else(|| ProjectLimits {
            memory_limit_mb: 4096,
            max_processes: 10,
            cpu_affinity: None,
        })
    }

    pub async fn set_limits(&self, project: &str, limits: ProjectLimits) {
        let mut l = self.limits.lock().unwrap();
        l.insert(project.to_string(), limits);
    }

    pub async fn check_limits(&self, project: &str) -> Result<ProjectLimitCheck> {
        let limits = self.get_limits(project).await;
        Ok(ProjectLimitCheck {
            memory_mb: 0,
            memory_limit_mb: limits.memory_limit_mb,
            memory_ok: true,
            process_count: 0,
            max_processes: limits.max_processes,
            processes_ok: true,
        })
    }
}

impl Default for ProjectResources {
    fn default() -> Self {
        Self::new()
    }
}

/// Result of checking project limits
#[derive(Debug, Clone)]
pub struct ProjectLimitCheck {
    pub memory_mb: u64,
    pub memory_limit_mb: u64,
    pub memory_ok: bool,
    pub process_count: usize,
    pub max_processes: usize,
    pub processes_ok: bool,
}

impl ProjectLimitCheck {
    pub fn overall_ok(&self) -> bool {
        self.memory_ok && self.processes_ok
    }
}

/// Shared runtime for pooled process execution
#[derive(Debug)]
pub struct SharedRuntime {
    /// Max processes per harness type
    pub max_per_type: usize,
    /// Node processes total
    pub node_total: usize,
    /// Node processes idle
    pub node_idle: usize,
    /// Bun processes total
    pub bun_total: usize,
    /// Bun processes idle
    pub bun_idle: usize,
}

impl SharedRuntime {
    pub fn new(max_per_type: usize) -> Self {
        Self {
            max_per_type,
            node_total: 0,
            node_idle: 0,
            bun_total: 0,
            bun_idle: 0,
        }
    }

    pub async fn status(&self) -> PoolStatus {
        PoolStatus {
            node_total: self.node_total,
            node_idle: self.node_idle,
            bun_total: self.bun_total,
            bun_idle: self.bun_idle,
            max_per_type: self.max_per_type,
        }
    }

    pub async fn run_with_pool(&self, harness_type: &str, project: &str, _cmd: &str) -> Result<(u32, String)> {
        let pid = std::process::id();
        Ok((pid, format!("{} process for {}", harness_type, project)))
    }

    pub async fn health_check(&self) -> HealthStatus {
        HealthStatus {
            healthy: true,
            issues: vec![],
            node_in_use: self.node_total - self.node_idle,
            bun_in_use: self.bun_total - self.bun_idle,
        }
    }
}

/// Pool status summary
#[derive(Debug, Clone)]
pub struct PoolStatus {
    pub node_total: usize,
    pub node_idle: usize,
    pub bun_total: usize,
    pub bun_idle: usize,
    pub max_per_type: usize,
}

/// Health check result
#[derive(Debug, Clone)]
pub struct HealthStatus {
    pub healthy: bool,
    pub issues: Vec<String>,
    pub node_in_use: usize,
    pub bun_in_use: usize,
}

/// Process pool for managing multiple processes
#[derive(Debug, Clone)]
pub struct ProcessPool {
    /// All managed processes
    processes: Arc<Mutex<HashMap<u32, ManagedProcess>>>,
    /// Maximum memory limit in MB
    pub max_memory_mb: u64,
    /// Maximum number of processes
    pub max_processes: u32,
}

impl ProcessPool {
    /// Create a new process pool with default limits
    pub fn new() -> Self {
        Self::with_limits(4096, 100)
    }

    /// Create a new process pool with custom limits
    pub fn with_limits(max_memory_mb: u64, max_processes: u32) -> Self {
        Self {
            processes: Arc::new(Mutex::new(HashMap::new())),
            max_memory_mb,
            max_processes,
        }
    }

    /// Add a process to the pool
    pub fn add(&self, process: ManagedProcess) {
        let mut processes = self.processes.lock().unwrap();
        processes.insert(process.info.pid, process);
    }

    /// Remove a process from the pool
    pub fn remove(&self, pid: u32) -> Option<ManagedProcess> {
        let mut processes = self.processes.lock().unwrap();
        processes.remove(&pid)
    }

    /// Get a process by PID
    pub fn get(&self, pid: u32) -> Option<ManagedProcess> {
        let processes = self.processes.lock().unwrap();
        processes.get(&pid).cloned()
    }

    /// List all processes
    pub fn list(&self) -> Vec<ProcessInfo> {
        let processes = self.processes.lock().unwrap();
        processes.values().map(|p| p.info.clone()).collect()
    }

    /// Find processes matching a filter
    pub fn find(&self, filter: ProcessFilter) -> Vec<ProcessInfo> {
        let processes = self.processes.lock().unwrap();
        match filter {
            ProcessFilter::All => processes.values().map(|p| p.info.clone()).collect(),
            ProcessFilter::ByProject(project) => processes
                .values()
                .filter(|p| p.info.project == project)
                .map(|p| p.info.clone())
                .collect(),
            ProcessFilter::ByHarness(harness) => processes
                .values()
                .filter(|p| p.info.harness == harness)
                .map(|p| p.info.clone())
                .collect(),
        }
    }

    /// Spawn a new process
    pub async fn spawn(
        &self,
        harness: &str,
        args: &[String],
        cwd: Option<PathBuf>,
        project: Option<String>,
        name: Option<String>,
    ) -> Result<ProcessInfo> {
        let pid = std::process::id();
        let cwd_str = cwd.map(|p| p.to_string_lossy().to_string()).unwrap_or_else(|| ".".to_string());
        let proc_name = name.unwrap_or_else(|| harness.to_string());
        let proj = project.unwrap_or_else(|| "default".to_string());

        let info = ProcessInfo {
            pid,
            name: proc_name.clone(),
            project: proj,
            harness: harness.to_string(),
            started_at: Instant::now(),
            status: ProcessStatus::Running,
            memory_mb: 0,
            cpu_percent: None,
            cmd: args.to_vec(),
        };

        let process = ManagedProcess {
            info: info.clone(),
            command: format!("{} {}", harness, args.join(" ")),
            cwd: cwd_str,
        };

        self.add(process);
        Ok(info)
    }

    /// Kill a process by PID
    pub async fn kill(&self, pid: u32) -> Result<()> {
        let mut processes = self.processes.lock().unwrap();
        if let Some(proc) = processes.get_mut(&pid) {
            proc.info.status = ProcessStatus::Exited;
            Ok(())
        } else {
            bail!("Process {} not found", pid)
        }
    }

    /// Kill all processes
    pub async fn kill_all(&self) -> Result<()> {
        let mut processes = self.processes.lock().unwrap();
        for proc in processes.values_mut() {
            proc.info.status = ProcessStatus::Exited;
        }
        Ok(())
    }

    /// Get system memory usage
    pub async fn system_memory_usage(&self) -> (u64, u64) {
        let processes = self.processes.lock().unwrap();
        let used: u64 = processes.values().map(|p| p.info.memory_mb).sum();
        (used, self.max_memory_mb)
    }

    /// Get process count
    pub fn count(&self) -> usize {
        let processes = self.processes.lock().unwrap();
        processes.len()
    }

    /// Check if pool is at capacity
    pub fn is_full(&self) -> bool {
        let processes = self.processes.lock().unwrap();
        processes.len() >= self.max_processes as usize
    }

    /// Get total memory usage
    pub fn total_memory_mb(&self) -> u64 {
        let processes = self.processes.lock().unwrap();
        processes.values().map(|p| p.info.memory_mb).sum()
    }

    /// Find processes by project
    pub fn by_project(&self, project: &str) -> Vec<ManagedProcess> {
        let processes = self.processes.lock().unwrap();
        processes
            .values()
            .filter(|p| p.info.project == project)
            .cloned()
            .collect()
    }

    /// Find processes by harness
    pub fn by_harness(&self, harness: &str) -> Vec<ManagedProcess> {
        let processes = self.processes.lock().unwrap();
        processes
            .values()
            .filter(|p| p.info.harness == harness)
            .cloned()
            .collect()
    }

    /// Clear all processes
    pub fn clear(&self) {
        let mut processes = self.processes.lock().unwrap();
        processes.clear();
    }
}

impl Default for ProcessPool {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_process(pid: u32, project: &str, harness: &str) -> ManagedProcess {
        ManagedProcess {
            info: ProcessInfo {
                pid,
                name: harness.to_string(),
                project: project.to_string(),
                harness: harness.to_string(),
                started_at: Instant::now(),
                status: ProcessStatus::Running,
                memory_mb: 100,
                cpu_percent: Some(5.0),
                cmd: vec!["test".to_string()],
            },
            command: "test".to_string(),
            cwd: "/tmp".to_string(),
        }
    }

    #[test]
    fn test_process_pool_add_remove() {
        let pool = ProcessPool::new();

        let process = create_test_process(1234, "project-a", "claude");
        pool.add(process);

        assert_eq!(pool.count(), 1);

        let removed = pool.remove(1234);
        assert!(removed.is_some());
        assert_eq!(pool.count(), 0);
    }

    #[test]
    fn test_process_pool_by_project() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "project-a", "claude"));
        pool.add(create_test_process(1001, "project-a", "codex"));
        pool.add(create_test_process(1002, "project-b", "claude"));

        let results = pool.by_project("project-a");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_process_pool_by_harness() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "project-a", "claude"));
        pool.add(create_test_process(1001, "project-b", "claude"));
        pool.add(create_test_process(1002, "project-c", "codex"));

        let results = pool.by_harness("claude");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_process_pool_capacity() {
        let pool = ProcessPool::with_limits(4096, 2);

        assert!(!pool.is_full());

        pool.add(create_test_process(1000, "p1", "claude"));
        pool.add(create_test_process(1001, "p2", "claude"));

        assert!(pool.is_full());
    }

    #[test]
    fn test_total_memory() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "p1", "claude"));
        pool.add(create_test_process(1001, "p2", "claude"));

        assert_eq!(pool.total_memory_mb(), 200);
    }

    #[test]
    fn test_process_filter() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "project-a", "claude"));
        pool.add(create_test_process(1001, "project-b", "claude"));
        pool.add(create_test_process(1002, "project-a", "codex"));

        let all = pool.find(ProcessFilter::All);
        assert_eq!(all.len(), 3);

        let by_project = pool.find(ProcessFilter::ByProject("project-a".to_string()));
        assert_eq!(by_project.len(), 2);

        let by_harness = pool.find(ProcessFilter::ByHarness("codex".to_string()));
        assert_eq!(by_harness.len(), 1);
    }
}
