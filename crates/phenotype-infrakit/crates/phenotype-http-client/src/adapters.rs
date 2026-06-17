//! HTTP client adapters
//!
//! This module contains adapter implementations for the HttpClientPort.
//! Currently supported:
//! - ReqwestAdapter: Production HTTP client using reqwest
//! - MockAdapter: Testing HTTP client that returns preconfigured responses

use crate::{
    error::{Error, Result},
    ports::HttpClientPort,
    types::{Body, ClientConfig, Headers, Request, Response},
};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Reqwest-based HTTP client adapter
#[cfg(feature = "reqwest-adapter")]
pub struct ReqwestAdapter {
    client: reqwest::Client,
    config: ClientConfig,
}

#[cfg(feature = "reqwest-adapter")]
impl ReqwestAdapter {
    /// Create a new adapter with default configuration
    pub fn new() -> Self {
        Self::with_config(ClientConfig::default())
    }

    /// Create a new adapter with custom configuration
    pub fn with_config(config: ClientConfig) -> Self {
        let client = reqwest::Client::builder()
            .timeout(config.timeout.request)
            .connect_timeout(config.timeout.connect)
            .redirect(if config.follow_redirects {
                reqwest::redirect::Policy::limited(config.max_redirects)
            } else {
                reqwest::redirect::Policy::none()
            })
            .build()
            .expect("Failed to build reqwest client");

        Self { client, config }
    }

    /// Create a new adapter with a preconfigured reqwest client
    pub fn from_client(client: reqwest::Client) -> Self {
        Self {
            client,
            config: ClientConfig::default(),
        }
    }
}

#[cfg(feature = "reqwest-adapter")]
impl Default for ReqwestAdapter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(feature = "reqwest-adapter")]
#[async_trait]
impl HttpClientPort for ReqwestAdapter {
    async fn execute(&self, request: Request) -> Result<Response> {
        let start = std::time::Instant::now();

        // Build the reqwest request
        let mut req_builder = self
            .client
            .request(request.method.into(), request.uri.to_string());

        // Add headers
        for (key, value) in request.headers.all() {
            req_builder = req_builder.header(key, value);
        }

        // Add default headers that aren't already set
        for (key, value) in self.config.default_headers.all() {
            if !request.headers.contains_key(key) {
                req_builder = req_builder.header(key, value);
            }
        }

        // Add user agent if configured
        if let Some(ref ua) = self.config.user_agent {
            if !request.headers.contains_key("user-agent") {
                req_builder = req_builder.header("user-agent", ua);
            }
        }

        // Add body if present
        if !request.body.is_empty() {
            req_builder = req_builder.body(request.body.as_bytes().to_vec());
        }

        // Execute the request
        let res = req_builder.send().await.map_err(|e| {
            if e.is_timeout() {
                Error::Timeout {
                    operation: "request".to_string(),
                    duration: self.config.timeout.request,
                }
            } else if e.is_connect() {
                Error::Connection(e.to_string())
            } else {
                Error::Network(e.to_string())
            }
        })?;

        // Convert response
        let status = res.status().as_u16();
        let headers = convert_headers(res.headers());
        let body_bytes = res
            .bytes()
            .await
            .map_err(|e| Error::Network(e.to_string()))?;
        let body = Body::from_bytes(body_bytes);
        let duration_ms = start.elapsed().as_millis() as u64;

        Ok(Response {
            status,
            headers,
            body,
            duration_ms,
        })
    }
}

#[cfg(feature = "reqwest-adapter")]
fn convert_headers(headers: &reqwest::header::HeaderMap) -> Headers {
    let mut result = Headers::new();
    for (key, value) in headers.iter() {
        if let Ok(value_str) = value.to_str() {
            result.insert(key.as_str(), value_str);
        }
    }
    result
}

/// Mock HTTP client for testing
pub struct MockAdapter {
    responses: Arc<Mutex<HashMap<String, Response>>>,
    default_response: Arc<Mutex<Option<Response>>>,
    request_log: Arc<Mutex<Vec<Request>>>,
}

impl MockAdapter {
    /// Create a new mock adapter
    pub fn new() -> Self {
        Self {
            responses: Arc::new(Mutex::new(HashMap::new())),
            default_response: Arc::new(Mutex::new(None)),
            request_log: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Configure a response for a specific URI
    pub fn when(&self, uri: impl Into<String>) -> MockResponseBuilder<'_> {
        MockResponseBuilder {
            adapter: self,
            uri: uri.into(),
        }
    }

    /// Set a default response for unmatched requests
    pub fn set_default_response(&self, response: Response) {
        if let Ok(mut guard) = self.default_response.lock() {
            *guard = Some(response);
        }
    }

    /// Get the request log
    pub fn request_log(&self) -> Vec<Request> {
        if let Ok(guard) = self.request_log.lock() {
            guard.clone()
        } else {
            Vec::new()
        }
    }

    /// Clear all configured responses
    pub fn clear(&self) {
        if let Ok(mut guard) = self.responses.lock() {
            guard.clear();
        }
        if let Ok(mut guard) = self.default_response.lock() {
            *guard = None;
        }
        if let Ok(mut guard) = self.request_log.lock() {
            guard.clear();
        }
    }

    /// Verify that a request was made to a specific URI
    pub fn was_requested(&self, uri: impl AsRef<str>) -> bool {
        if let Ok(guard) = self.request_log.lock() {
            guard.iter().any(|r| r.uri.to_string() == uri.as_ref())
        } else {
            false
        }
    }

    /// Get the number of requests made
    pub fn request_count(&self) -> usize {
        if let Ok(guard) = self.request_log.lock() {
            guard.len()
        } else {
            0
        }
    }
}

impl Default for MockAdapter {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl HttpClientPort for MockAdapter {
    async fn execute(&self, request: Request) -> Result<Response> {
        // Log the request
        if let Ok(mut guard) = self.request_log.lock() {
            guard.push(request.clone());
        }

        // Look up response
        let uri = request.uri.to_string();

        if let Ok(guard) = self.responses.lock() {
            if let Some(response) = guard.get(&uri) {
                return Ok(response.clone());
            }
        }

        // Return default response if set
        if let Ok(guard) = self.default_response.lock() {
            if let Some(response) = guard.clone() {
                return Ok(response);
            }
        }

        // Return 404 if no response configured
        Ok(Response {
            status: 404,
            headers: Headers::new(),
            body: Body::from_string(format!("No mock response configured for {}", uri)),
            duration_ms: 0,
        })
    }
}

/// Builder for configuring mock responses
pub struct MockResponseBuilder<'a> {
    adapter: &'a MockAdapter,
    uri: String,
}

impl<'a> MockResponseBuilder<'a> {
    /// Set the response status
    pub fn then_return(self, response: Response) -> &'a MockAdapter {
        if let Ok(mut guard) = self.adapter.responses.lock() {
            guard.insert(self.uri, response);
        }
        self.adapter
    }

    /// Set a successful JSON response
    pub fn then_return_json<T: serde::Serialize>(self, body: &T) -> Result<&'a MockAdapter> {
        let body = Body::from_json(body)?;
        let response = Response {
            status: 200,
            headers: {
                let mut h = Headers::new();
                h.insert("content-type", "application/json");
                h
            },
            body,
            duration_ms: 0,
        };
        if let Ok(mut guard) = self.adapter.responses.lock() {
            guard.insert(self.uri, response);
        }
        Ok(self.adapter)
    }

    /// Set an error response
    pub fn then_return_error(self, status: u16, message: impl Into<String>) -> &'a MockAdapter {
        let response = Response {
            status,
            headers: Headers::new(),
            body: Body::from_string(message),
            duration_ms: 0,
        };
        if let Ok(mut guard) = self.adapter.responses.lock() {
            guard.insert(self.uri, response);
        }
        self.adapter
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::Method;

    #[tokio::test]
    async fn test_mock_adapter() {
        let mock = MockAdapter::new();

        // Configure response
        mock.when("https://api.example.com/users")
            .then_return(Response {
                status: 200,
                headers: Headers::new(),
                body: Body::from_string(r#"{"users": []}"#),
                duration_ms: 0,
            });

        // Make request
        let request = Request::builder()
            .method(Method::GET)
            .uri("https://api.example.com/users")
            .build()
            .unwrap();

        let response = mock.execute(request).await.unwrap();
        assert_eq!(response.status, 200);
        assert!(mock.was_requested("https://api.example.com/users"));
    }

    #[test]
    fn test_mock_adapter_request_log() {
        let mock = MockAdapter::new();
        assert_eq!(mock.request_count(), 0);

        // Verify the request log starts empty
        assert!(mock.request_log().is_empty());
    }
}
