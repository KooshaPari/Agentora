//! Phenotype Daemon - High-performance sidecar for skill management
//! 
//! Architecture:
//! - Unix domain sockets (fast local IPC)
//! - TCP fallback for cross-platform compatibility
//! - msgpack-rpc protocol for efficient serialization
//! - Async I/O with tokio for high concurrency

mod protocol;
mod rpc;

use rpc::{RpcHandler, SharedState};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::net::{TcpListener, UnixListener};
use tracing::{error, info, warn};

use protocol::VersionInfo;

/// Default socket path for Unix domain sockets
#[cfg(unix)]
const DEFAULT_SOCKET_PATH: &str = "/tmp/phenotype-daemon.sock";

/// Default TCP port for cross-platform support
const DEFAULT_TCP_PORT: u16 = 9456;

/// Server configuration
#[derive(Debug, Clone)]
struct ServerConfig {
    /// Unix socket path (Unix only)
    #[cfg(unix)]
    socket_path: PathBuf,
    /// TCP port for fallback
    tcp_port: u16,
    /// Enable TCP mode (Windows requires this)
    tcp_only: bool,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            #[cfg(unix)]
            socket_path: PathBuf::from(DEFAULT_SOCKET_PATH),
            tcp_port: DEFAULT_TCP_PORT,
            tcp_only: cfg!(windows),
        }
    }
}

/// Initialize logging with appropriate level
fn init_logging() {
    let filter = std::env::var("RUST_LOG")
        .unwrap_or_else(|_| "info".to_string());
    
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .init();
}

/// Run Unix socket server
#[cfg(unix)]
async fn run_unix_server(
    config: &ServerConfig,
    state: Arc<SharedState>,
) -> anyhow::Result<()> {
    // Remove existing socket if present
    if config.socket_path.exists() {
        tokio::fs::remove_file(&config.socket_path).await.ok();
    }

    let listener = UnixListener::bind(&config.socket_path)?;
    info!("Unix socket listening at {:?}", config.socket_path);

    loop {
        let (stream, _) = listener.accept().await?;
        let state = state.clone();

        tokio::spawn(async move {
            let mut handler = RpcHandler::new(state);
            if let Err(e) = handler.handle_stream(stream).await {
                error!("Connection error: {}", e);
            }
        });
    }
}

/// Run TCP server
async fn run_tcp_server(
    config: &ServerConfig,
    state: Arc<SharedState>,
) -> anyhow::Result<()> {
    let addr = format!("127.0.0.1:{}", config.tcp_port);
    let listener = TcpListener::bind(&addr).await?;
    info!("TCP server listening on {}", addr);

    loop {
        let (stream, peer) = listener.accept().await?;
        info!("New TCP connection from {:?}", peer);

        let mut handler = RpcHandler::new(state.clone());

        tokio::spawn(async move {
            if let Err(e) = handler.handle_stream(stream).await {
                error!("Connection error from {:?}: {}", peer, e);
            }
        });
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_logging();

    info!("Starting Phenotype Daemon v{}", VersionInfo::current().version);

    let config = ServerConfig::default();
    let state = Arc::new(SharedState::new());

    // Spawn TCP server (always available for fallback)
    let tcp_state = state.clone();
    let tcp_config = config.clone();
    let tcp_handle = tokio::spawn(async move {
        if let Err(e) = run_tcp_server(&tcp_config, tcp_state).await {
            error!("TCP server error: {}", e);
        }
    });

    // Spawn Unix socket server (Unix only)
    #[cfg(unix)]
    let unix_handle = if !config.tcp_only {
        let unix_state = state.clone();
        let unix_config = config.clone();
        Some(tokio::spawn(async move {
            if let Err(e) = run_unix_server(&unix_config, unix_state).await {
                error!("Unix socket server error: {}", e);
            }
        }))
    } else {
        None
    };

    info!("Daemon ready - waiting for connections");

    // Wait for all servers
    tokio::select! {
        _ = tcp_handle => {
            warn!("TCP server exited");
        }
        _ = async {
            if let Some(h) = unix_handle {
                let _ = h.await;
            }
            std::future::pending::<()>().await;
        } => {}
    }

    Ok(())
}
