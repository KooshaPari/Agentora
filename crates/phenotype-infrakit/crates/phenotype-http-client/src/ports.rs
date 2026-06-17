//! Domain ports (interfaces) for the HTTP client
//!
//! Ports define the boundaries between the domain and the infrastructure.
//! They are traits that specify what operations the domain needs.

use crate::{
    error::Result,
    types::{Request, Response},
};
use async_trait::async_trait;

/// Primary inbound port - what the HTTP client can do
///
/// This trait defines the contract that all HTTP client implementations
/// must fulfill. It is intentionally simple to allow for various backends
/// (reqwest, hyper, mock, etc.).
///
/// Traces to: FR-HTTP-004
#[async_trait]
pub trait HttpClientPort: Send + Sync {
    /// Execute an HTTP request and return the response
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use phenotype_http_client::{HttpClientPort, Request, Method};
    ///
    /// async fn example<C: HttpClientPort>(client: &C) {
    ///     let request = Request::builder()
    ///         .method(Method::GET)
    ///         .uri("https://example.com")
    ///         .build()
    ///         .unwrap();
    ///     
    ///     let response = client.execute(request).await.unwrap();
    ///     assert_eq!(response.status, 200);
    /// }
    /// ```
    async fn execute(&self, request: Request) -> Result<Response>;

    /// Convenience method for GET requests
    async fn get(&self, uri: &str) -> Result<Response> {
        let request = Request::builder()
            .method(http::Method::GET)
            .uri(uri)
            .build()?;
        self.execute(request).await
    }

    /// Convenience method for POST requests
    async fn post(&self, uri: &str, body: crate::types::Body) -> Result<Response> {
        let request = Request::builder()
            .method(http::Method::POST)
            .uri(uri)
            .body(body)
            .build()?;
        self.execute(request).await
    }

    /// Convenience method for PUT requests
    async fn put(&self, uri: &str, body: crate::types::Body) -> Result<Response> {
        let request = Request::builder()
            .method(http::Method::PUT)
            .uri(uri)
            .body(body)
            .build()?;
        self.execute(request).await
    }

    /// Convenience method for DELETE requests
    async fn delete(&self, uri: &str) -> Result<Response> {
        let request = Request::builder()
            .method(http::Method::DELETE)
            .uri(uri)
            .build()?;
        self.execute(request).await
    }

    /// Convenience method for PATCH requests
    async fn patch(&self, uri: &str, body: crate::types::Body) -> Result<Response> {
        let request = Request::builder()
            .method(http::Method::PATCH)
            .uri(uri)
            .body(body)
            .build()?;
        self.execute(request).await
    }
}

/// Outbound port for request/response interceptors
///
/// Interceptors can modify requests before they are sent and
/// responses after they are received.
///
/// Traces to: FR-HTTP-005
#[async_trait]
pub trait InterceptorPort: Send + Sync {
    /// Error type for interceptor operations
    type Error: std::error::Error + Send + Sync;

    /// Intercept and potentially modify a request
    async fn intercept_request(
        &self,
        request: Request,
    ) -> std::result::Result<Request, Self::Error>;

    /// Intercept and potentially modify a response
    async fn intercept_response(
        &self,
        response: Response,
    ) -> std::result::Result<Response, Self::Error>;
}

/// Port for connection pooling management
///
/// Traces to: FR-HTTP-006
pub trait ConnectionPoolPort: Send + Sync {
    /// Get a connection from the pool
    fn acquire(&self) -> Result<Box<dyn ConnectionPort>>;

    /// Return statistics about the pool
    fn stats(&self) -> PoolStats;
}

/// Port for individual connections
///
/// Traces to: FR-HTTP-007
pub trait ConnectionPort: Send + Sync {
    /// Check if the connection is still alive
    fn is_alive(&self) -> bool;

    /// Close the connection
    fn close(&self) -> Result<()>;
}

/// Statistics for connection pool
#[derive(Debug, Clone, Default)]
pub struct PoolStats {
    /// Total connections in pool
    pub total_connections: usize,
    /// Available (idle) connections
    pub available_connections: usize,
    /// Active (in-use) connections
    pub active_connections: usize,
    /// Total requests served
    pub requests_served: u64,
}
