//! HTTP client port traits — contract surface for transport adapters.
//!
//! Extracted from `phenotype-http-client` ports; implementations live in
//! infrastructure crates (reqwest, mock, etc.).

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;
use thiserror::Error;

/// HTTP-layer contract error.
#[derive(Error, Debug, Clone)]
pub enum HttpError {
    /// Request failed before a response was received.
    #[error("network error: {0}")]
    Network(String),
    /// Connection could not be established.
    #[error("connection error: {0}")]
    Connection(String),
    /// Request timed out.
    #[error("timeout during {operation} after {duration:?}")]
    Timeout {
        /// Operation that timed out.
        operation: String,
        /// Configured timeout duration.
        duration: Duration,
    },
    /// Invalid request construction.
    #[error("invalid request: {0}")]
    InvalidRequest(String),
}

/// Result type for HTTP contract operations.
pub type Result<T> = std::result::Result<T, HttpError>;

/// HTTP request body.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Body {
    bytes: Vec<u8>,
}

impl Body {
    /// Empty body.
    pub fn empty() -> Self {
        Self { bytes: Vec::new() }
    }

    /// Body from raw bytes.
    pub fn from_bytes(bytes: impl Into<Vec<u8>>) -> Self {
        Self {
            bytes: bytes.into(),
        }
    }

    /// Body from UTF-8 string.
    pub fn from_string(content: impl Into<String>) -> Self {
        Self {
            bytes: content.into().into_bytes(),
        }
    }

    /// Body from JSON-serializable value.
    pub fn from_json<T: Serialize>(value: &T) -> Result<Self> {
        serde_json::to_vec(value)
            .map(|bytes| Self { bytes })
            .map_err(|e| HttpError::InvalidRequest(e.to_string()))
    }

    /// Returns true when the body has no content.
    pub fn is_empty(&self) -> bool {
        self.bytes.is_empty()
    }

    /// Raw body bytes.
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes
    }
}

/// HTTP header map (case-insensitive keys stored as provided).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Headers {
    inner: HashMap<String, String>,
}

impl Headers {
    /// Create empty headers.
    pub fn new() -> Self {
        Self {
            inner: HashMap::new(),
        }
    }

    /// Insert a header.
    pub fn insert(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.inner.insert(key.into(), value.into());
    }

    /// Get a header value.
    pub fn get(&self, key: &str) -> Option<&str> {
        self.inner.get(key).map(String::as_str)
    }

    /// Whether a header is present.
    pub fn contains_key(&self, key: &str) -> bool {
        self.inner.contains_key(key)
    }

    /// Iterate all header pairs.
    pub fn all(&self) -> impl Iterator<Item = (&str, &str)> {
        self.inner
            .iter()
            .map(|(k, v)| (k.as_str(), v.as_str()))
    }
}

/// HTTP request contract type.
#[derive(Debug, Clone)]
pub struct Request {
    /// HTTP method.
    pub method: http::Method,
    /// Request URI.
    pub uri: String,
    /// Request headers.
    pub headers: Headers,
    /// Request body.
    pub body: Body,
    /// Per-request timeout override.
    pub timeout: Option<Duration>,
}

impl Request {
    /// Create a request builder.
    pub fn builder() -> RequestBuilder {
        RequestBuilder::new()
    }
}

/// Fluent request builder.
#[derive(Debug, Default)]
pub struct RequestBuilder {
    method: Option<http::Method>,
    uri: Option<String>,
    headers: Headers,
    body: Body,
    timeout: Option<Duration>,
}

impl RequestBuilder {
    /// Create a new builder defaulting to GET.
    pub fn new() -> Self {
        Self {
            method: Some(http::Method::GET),
            ..Default::default()
        }
    }

    /// Set HTTP method.
    pub fn method(mut self, method: http::Method) -> Self {
        self.method = Some(method);
        self
    }

    /// Set request URI.
    pub fn uri(mut self, uri: impl Into<String>) -> Self {
        self.uri = Some(uri.into());
        self
    }

    /// Set request body.
    pub fn body(mut self, body: Body) -> Self {
        self.body = body;
        self
    }

    /// Build the request.
    pub fn build(self) -> Result<Request> {
        Ok(Request {
            method: self.method.unwrap_or(http::Method::GET),
            uri: self
                .uri
                .ok_or_else(|| HttpError::InvalidRequest("uri is required".into()))?,
            headers: self.headers,
            body: self.body,
            timeout: self.timeout,
        })
    }
}

/// HTTP response contract type.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Response {
    /// HTTP status code.
    pub status: u16,
    /// Response headers.
    pub headers: Headers,
    /// Response body.
    pub body: Body,
    /// Round-trip duration in milliseconds.
    pub duration_ms: u64,
}

/// Primary inbound port — what HTTP client implementations must provide.
#[async_trait]
pub trait HttpClientPort: Send + Sync {
    /// Execute an HTTP request and return the response.
    async fn execute(&self, request: Request) -> Result<Response>;

    /// Convenience GET.
    async fn get(&self, uri: &str) -> Result<Response> {
        let request = Request::builder().method(http::Method::GET).uri(uri).build()?;
        self.execute(request).await
    }

    /// Convenience POST.
    async fn post(&self, uri: &str, body: Body) -> Result<Response> {
        let request = Request::builder()
            .method(http::Method::POST)
            .uri(uri)
            .body(body)
            .build()?;
        self.execute(request).await
    }
}

/// Outbound port for request/response interceptors.
#[async_trait]
pub trait InterceptorPort: Send + Sync {
    /// Interceptor error type.
    type Error: std::error::Error + Send + Sync;

    /// Intercept and potentially modify a request.
    async fn intercept_request(
        &self,
        request: Request,
    ) -> std::result::Result<Request, Self::Error>;

    /// Intercept and potentially modify a response.
    async fn intercept_response(
        &self,
        response: Response,
    ) -> std::result::Result<Response, Self::Error>;
}

/// Connection pool statistics.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PoolStats {
    /// Total connections in pool.
    pub total_connections: usize,
    /// Available (idle) connections.
    pub available_connections: usize,
    /// Active (in-use) connections.
    pub active_connections: usize,
    /// Total requests served.
    pub requests_served: u64,
}

/// Port for connection pooling management.
pub trait ConnectionPoolPort: Send + Sync {
    /// Return statistics about the pool.
    fn stats(&self) -> PoolStats;
}

/// Port for individual pooled connections.
pub trait ConnectionPort: Send + Sync {
    /// Check if the connection is still alive.
    fn is_alive(&self) -> bool;
}

#[cfg(test)]
mod tests {
    use super::*;

    struct EchoClient;

    #[async_trait]
    impl HttpClientPort for EchoClient {
        async fn execute(&self, request: Request) -> Result<Response> {
            Ok(Response {
                status: 200,
                headers: Headers::new(),
                body: request.body,
                duration_ms: 0,
            })
        }
    }

    #[tokio::test]
    async fn http_client_port_get() {
        let client = EchoClient;
        let response = client.get("https://example.com").await.unwrap();
        assert_eq!(response.status, 200);
    }
}
