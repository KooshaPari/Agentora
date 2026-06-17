//! HTTP types - Request, Response, Method, Body, etc.

use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// HTTP request
#[derive(Debug, Clone)]
pub struct Request {
    /// HTTP method
    pub method: Method,
    /// Request URI
    pub uri: Uri,
    /// Request headers
    pub headers: Headers,
    /// Request body
    pub body: Body,
    /// Request timeout
    pub timeout: Option<std::time::Duration>,
}

impl Request {
    /// Create a request builder
    pub fn builder() -> RequestBuilder {
        RequestBuilder::new()
    }

    /// Get the content type header
    pub fn content_type(&self) -> Option<&str> {
        self.headers.get("content-type").map(|v| v.as_str())
    }
}

/// Request builder
#[derive(Debug, Default)]
pub struct RequestBuilder {
    method: Option<Method>,
    uri: Option<Uri>,
    headers: Headers,
    body: Body,
    timeout: Option<std::time::Duration>,
}

impl RequestBuilder {
    /// Create a new builder
    pub fn new() -> Self {
        Self {
            method: Some(Method::GET),
            uri: None,
            headers: Headers::new(),
            body: Body::empty(),
            timeout: None,
        }
    }

    /// Set the HTTP method
    pub fn method(mut self, method: impl Into<Method>) -> Self {
        self.method = Some(method.into());
        self
    }

    /// Set the URI
    pub fn uri(mut self, uri: impl Into<Uri>) -> Self {
        self.uri = Some(uri.into());
        self
    }

    /// Add a header
    pub fn header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.insert(key, value);
        self
    }

    /// Set multiple headers
    pub fn headers(mut self, headers: Headers) -> Self {
        self.headers = headers;
        self
    }

    /// Set the request body
    pub fn body(mut self, body: impl Into<Body>) -> Self {
        self.body = body.into();
        self
    }

    /// Set the timeout
    pub fn timeout(mut self, timeout: std::time::Duration) -> Self {
        self.timeout = Some(timeout);
        self
    }

    /// Build the request
    pub fn build(self) -> Result<Request> {
        Ok(Request {
            method: self
                .method
                .ok_or_else(|| Error::request("Method is required"))?,
            uri: self.uri.ok_or_else(|| Error::request("URI is required"))?,
            headers: self.headers,
            body: self.body,
            timeout: self.timeout,
        })
    }
}

/// HTTP response
#[derive(Debug, Clone)]
pub struct Response {
    /// HTTP status code
    pub status: u16,
    /// Response headers
    pub headers: Headers,
    /// Response body
    pub body: Body,
    /// Response duration
    pub duration_ms: u64,
}

impl Response {
    /// Check if the response was successful (2xx)
    pub fn is_success(&self) -> bool {
        (200..300).contains(&self.status)
    }

    /// Check if the response was a client error (4xx)
    pub fn is_client_error(&self) -> bool {
        (400..500).contains(&self.status)
    }

    /// Check if the response was a server error (5xx)
    pub fn is_server_error(&self) -> bool {
        (500..600).contains(&self.status)
    }

    /// Parse the body as JSON
    pub fn json<T: serde::de::DeserializeOwned>(&self) -> Result<T> {
        self.body.parse_json()
    }

    /// Get the body as text
    pub fn text(&self) -> Result<String> {
        self.body.text()
    }
}

/// HTTP method
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
#[allow(clippy::upper_case_acronyms)]
pub enum Method {
    /// GET
    GET,
    /// POST
    POST,
    /// PUT
    PUT,
    /// DELETE
    DELETE,
    /// PATCH
    PATCH,
    /// HEAD
    HEAD,
    /// OPTIONS
    OPTIONS,
    /// TRACE
    TRACE,
    /// CONNECT
    CONNECT,
}

impl Method {
    /// Get the method as a string
    pub fn as_str(&self) -> &str {
        match self {
            Method::GET => "GET",
            Method::POST => "POST",
            Method::PUT => "PUT",
            Method::DELETE => "DELETE",
            Method::PATCH => "PATCH",
            Method::HEAD => "HEAD",
            Method::OPTIONS => "OPTIONS",
            Method::TRACE => "TRACE",
            Method::CONNECT => "CONNECT",
        }
    }
}

impl From<http::Method> for Method {
    fn from(m: http::Method) -> Self {
        match m {
            http::Method::GET => Method::GET,
            http::Method::POST => Method::POST,
            http::Method::PUT => Method::PUT,
            http::Method::DELETE => Method::DELETE,
            http::Method::PATCH => Method::PATCH,
            http::Method::HEAD => Method::HEAD,
            http::Method::OPTIONS => Method::OPTIONS,
            http::Method::TRACE => Method::TRACE,
            http::Method::CONNECT => Method::CONNECT,
            _ => Method::GET,
        }
    }
}

impl From<Method> for http::Method {
    fn from(m: Method) -> Self {
        match m {
            Method::GET => http::Method::GET,
            Method::POST => http::Method::POST,
            Method::PUT => http::Method::PUT,
            Method::DELETE => http::Method::DELETE,
            Method::PATCH => http::Method::PATCH,
            Method::HEAD => http::Method::HEAD,
            Method::OPTIONS => http::Method::OPTIONS,
            Method::TRACE => http::Method::TRACE,
            Method::CONNECT => http::Method::CONNECT,
        }
    }
}

/// HTTP headers
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Headers {
    inner: HashMap<String, String>,
}

impl Headers {
    /// Create new empty headers
    pub fn new() -> Self {
        Self {
            inner: HashMap::new(),
        }
    }

    /// Insert a header
    pub fn insert(&mut self, key: impl Into<String>, value: impl Into<String>) -> Option<String> {
        self.inner.insert(key.into().to_lowercase(), value.into())
    }

    /// Get a header value
    pub fn get(&self, key: impl AsRef<str>) -> Option<&String> {
        self.inner.get(key.as_ref().to_lowercase().as_str())
    }

    /// Check if a header exists
    pub fn contains_key(&self, key: impl AsRef<str>) -> bool {
        self.inner
            .contains_key(key.as_ref().to_lowercase().as_str())
    }

    /// Remove a header
    pub fn remove(&mut self, key: impl AsRef<str>) -> Option<String> {
        self.inner.remove(key.as_ref().to_lowercase().as_str())
    }

    /// Get all headers
    pub fn all(&self) -> &HashMap<String, String> {
        &self.inner
    }
}

impl From<HashMap<String, String>> for Headers {
    fn from(inner: HashMap<String, String>) -> Self {
        Self { inner }
    }
}

/// HTTP request/response body
#[derive(Debug, Clone, Default)]
pub struct Body {
    inner: Vec<u8>,
}

impl Body {
    /// Create an empty body
    pub fn empty() -> Self {
        Self { inner: Vec::new() }
    }

    /// Create a body from bytes
    pub fn from_bytes(bytes: impl AsRef<[u8]>) -> Self {
        Self {
            inner: bytes.as_ref().to_vec(),
        }
    }

    /// Create a body from a string
    pub fn from_string(s: impl Into<String>) -> Self {
        let s = s.into();
        Self {
            inner: s.into_bytes(),
        }
    }

    /// Create a JSON body
    pub fn from_json<T: serde::Serialize>(value: &T) -> Result<Self> {
        let json = serde_json::to_vec(value).map_err(|e| Error::serialization(e.to_string()))?;
        Ok(Self { inner: json })
    }

    /// Get the body as bytes
    pub fn as_bytes(&self) -> &[u8] {
        &self.inner
    }

    /// Get the body as a string
    pub fn as_str(&self) -> Result<&str> {
        std::str::from_utf8(&self.inner)
            .map_err(|e| Error::serialization(format!("Invalid UTF-8: {}", e)))
    }

    /// Parse the body as JSON
    pub fn parse_json<T: serde::de::DeserializeOwned>(&self) -> Result<T> {
        serde_json::from_slice(&self.inner)
            .map_err(|e| Error::serialization(format!("JSON parse error: {}", e)))
    }

    /// Get the body as text
    pub fn text(&self) -> Result<String> {
        Ok(String::from_utf8_lossy(&self.inner).to_string())
    }

    /// Get the content length
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Check if body is empty
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

impl From<Vec<u8>> for Body {
    fn from(inner: Vec<u8>) -> Self {
        Self { inner }
    }
}

impl From<String> for Body {
    fn from(s: String) -> Self {
        Self::from_string(s)
    }
}

impl From<&str> for Body {
    fn from(s: &str) -> Self {
        Self::from_string(s)
    }
}

impl From<&[u8]> for Body {
    fn from(s: &[u8]) -> Self {
        Self::from_bytes(s)
    }
}

/// URI
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Uri {
    inner: String,
}

impl Uri {
    /// Create a new URI
    pub fn new(uri: impl Into<String>) -> Self {
        Self { inner: uri.into() }
    }

    /// Parse a URI
    pub fn parse(uri: impl AsRef<str>) -> Result<Self> {
        let s = uri.as_ref();
        // Basic validation
        if !s.starts_with("http://") && !s.starts_with("https://") {
            return Err(Error::request(format!("Invalid URI scheme: {}", s)));
        }
        Ok(Self::new(s))
    }

    /// Get the scheme (http/https)
    pub fn scheme(&self) -> Option<&str> {
        if self.inner.starts_with("https://") {
            Some("https")
        } else if self.inner.starts_with("http://") {
            Some("http")
        } else {
            None
        }
    }

    /// Get the host
    pub fn host(&self) -> Option<&str> {
        self.inner
            .trim_start_matches("http://")
            .trim_start_matches("https://")
            .split('/')
            .next()
            .map(|s| s.split(':').next().unwrap_or(s))
    }
}

impl std::fmt::Display for Uri {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.inner)
    }
}

impl From<String> for Uri {
    fn from(s: String) -> Self {
        Self::new(s)
    }
}

impl From<&str> for Uri {
    fn from(s: &str) -> Self {
        Self::new(s)
    }
}

/// Timeout configuration
#[derive(Debug, Clone, Copy)]
pub struct TimeoutConfig {
    /// Connect timeout
    pub connect: std::time::Duration,
    /// Request timeout
    pub request: std::time::Duration,
    /// Read timeout
    pub read: std::time::Duration,
    /// Write timeout
    pub write: std::time::Duration,
}

impl Default for TimeoutConfig {
    fn default() -> Self {
        Self {
            connect: std::time::Duration::from_secs(30),
            request: std::time::Duration::from_secs(30),
            read: std::time::Duration::from_secs(30),
            write: std::time::Duration::from_secs(30),
        }
    }
}

impl TimeoutConfig {
    /// Create with all timeouts set to the same value
    pub fn all(timeout: std::time::Duration) -> Self {
        Self {
            connect: timeout,
            request: timeout,
            read: timeout,
            write: timeout,
        }
    }
}

/// Client configuration
#[derive(Debug, Clone)]
pub struct ClientConfig {
    /// Timeout configuration
    pub timeout: TimeoutConfig,
    /// Default headers
    pub default_headers: Headers,
    /// Follow redirects
    pub follow_redirects: bool,
    /// Max redirects
    pub max_redirects: usize,
    /// User agent
    pub user_agent: Option<String>,
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self {
            timeout: TimeoutConfig::default(),
            default_headers: Headers::new(),
            follow_redirects: true,
            max_redirects: 10,
            user_agent: Some("phenotype-http-client/0.1.0".to_string()),
        }
    }
}
