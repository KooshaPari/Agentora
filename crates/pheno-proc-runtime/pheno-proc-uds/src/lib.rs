//! Unix Domain Socket IPC for PhenoProc

use std::path::Path;
use tokio::net::{UnixListener, UnixStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use thiserror::Error;

/// UDS IPC error
#[derive(Debug, Error)]
pub enum UdsError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("connection closed")]
    ConnectionClosed,
    #[error("invalid message")]
    InvalidMessage,
}

/// UDS server
pub struct UdsServer {
    listener: UnixListener,
}

impl UdsServer {
    pub async fn bind<P: AsRef<Path>>(path: P) -> Result<Self, UdsError> {
        // Remove old socket file if exists
        let _ = std::fs::remove_file(&path);
        let listener = UnixListener::bind(path)?;
        Ok(Self { listener })
    }

    pub async fn accept(&self) -> Result<UdsStream, UdsError> {
        let (stream, _) = self.listener.accept().await?;
        Ok(UdsStream { stream })
    }
}

/// UDS client stream
pub struct UdsStream {
    stream: UnixStream,
}

impl UdsStream {
    pub async fn connect<P: AsRef<Path>>(path: P) -> Result<Self, UdsError> {
        let stream = UnixStream::connect(path).await?;
        Ok(Self { stream })
    }

    pub async fn send(&mut self, data: &[u8]) -> Result<(), UdsError> {
        self.stream.write_all(data).await?;
        Ok(())
    }

    pub async fn recv(&mut self, buf: &mut [u8]) -> Result<usize, UdsError> {
        let n = self.stream.read(buf).await?;
        Ok(n)
    }

    pub async fn send_msg(&mut self, msg: &str) -> Result<(), UdsError> {
        let data = msg.as_bytes();
        let len = data.len() as u32;
        self.stream.write_all(&len.to_be_bytes()).await?;
        self.stream.write_all(data).await?;
        Ok(())
    }

    pub async fn recv_msg(&mut self) -> Result<String, UdsError> {
        let mut len_buf = [0u8; 4];
        let n = self.stream.read_exact(&mut len_buf).await?;
        if n == 0 {
            return Err(UdsError::ConnectionClosed);
        }
        let len = u32::from_be_bytes(len_buf) as usize;
        
        let mut buf = vec![0u8; len];
        self.stream.read_exact(&mut buf).await?;
        
        String::from_utf8(buf).map_err(|_| UdsError::InvalidMessage)
    }
}

/// UDS message codec
#[derive(Debug, Clone)]
pub struct Message {
    pub payload: Vec<u8>,
}

impl Message {
    pub fn new(payload: Vec<u8>) -> Self {
        Self { payload }
    }

    pub fn from_string(s: &str) -> Self {
        Self::new(s.as_bytes().to_vec())
    }

    pub fn to_string(&self) -> Result<String, std::string::FromUtf8Error> {
        String::from_utf8(self.payload.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use tokio::time::timeout;

    #[tokio::test]
    async fn test_uds_basic() {
        let socket_path = "/tmp/test_uds_basic.sock";
        let _ = std::fs::remove_file(socket_path);

        let server = UdsServer::bind(socket_path).await.unwrap();
        
        // Spawn server
        let server_handle = tokio::spawn(async move {
            let mut stream = server.accept().await.unwrap();
            let msg = stream.recv_msg().await.unwrap();
            assert_eq!(msg, "hello");
            stream.send_msg("world").await.unwrap();
        });

        // Client
        let client_handle = tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(100)).await;
            let mut stream = UdsStream::connect(socket_path).await.unwrap();
            stream.send_msg("hello").await.unwrap();
            let response = stream.recv_msg().await.unwrap();
            assert_eq!(response, "world");
        });

        let _ = timeout(Duration::from_secs(5), async {
            let (r1, r2) = tokio::join!(server_handle, client_handle);
            r1.unwrap();
            r2.unwrap();
        }).await;

        let _ = std::fs::remove_file(socket_path);
    }
}
