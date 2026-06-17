//! HTTP client with retry and timeout support

pub mod error;

pub use error::{HttpError, Result};
use std::time::Duration;
use reqwest::Client;

/// Configuration for HTTP client
#[derive(Debug, Clone)]
pub struct HttpConfig {
    pub timeout: Duration,
    pub max_retries: u32,
    pub retry_delay: Duration,
}

impl Default for HttpConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            max_retries: 3,
            retry_delay: Duration::from_millis(100),
        }
    }
}

/// HTTP client wrapper
pub struct HttpClient {
    client: Client,
    config: HttpConfig,
}

impl HttpClient {
    /// Creates a new HTTP client with default configuration
    pub fn new() -> Self {
        Self::with_config(HttpConfig::default())
    }

    /// Creates a new HTTP client with the given configuration
    pub fn with_config(config: HttpConfig) -> Self {
        let client = Client::builder()
            .timeout(config.timeout)
            .build()
            .unwrap_or_else(|_| Client::new());
        Self { client, config }
    }

    /// Performs a GET request with retries
    pub async fn get(&self, url: &str) -> Result<String> {
        let mut attempts = 0;
        loop {
            match self.client.get(url).send().await {
                Ok(resp) => {
                    let status = resp.status();
                    if status.is_success() {
                        return Ok(resp.text().await?);
                    }
                    if attempts >= self.config.max_retries || !status.is_server_error() {
                        return Err(HttpError::Status(status.as_u16()));
                    }
                }
                Err(e) => {
                    if attempts >= self.config.max_retries {
                        return Err(HttpError::Request(e));
                    }
                }
            }
            attempts += 1;
            tokio::time::sleep(self.config.retry_delay).await;
        }
    }
}

impl Default for HttpClient {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    #[tokio::test]
    async fn test_get_success() {
        let mock_server = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/test"))
            .respond_with(ResponseTemplate::new(200).set_body_string("success"))
            .mount(&mock_server)
            .await;

        let client = HttpClient::new();
        let result = client.get(&format!("{}/test", &mock_server.uri())).await;
        assert_eq!(result.unwrap(), "success");
    }

    #[tokio::test]
    async fn test_get_retry_on_server_error() {
        let mock_server = MockServer::start().await;
        
        // Return 500 once, then 200
        Mock::given(method("GET"))
            .and(path("/retry"))
            .respond_with(ResponseTemplate::new(500))
            .expect(1)
            .mount(&mock_server)
            .await;
            
        Mock::given(method("GET"))
            .and(path("/retry"))
            .respond_with(ResponseTemplate::new(200).set_body_string("recovered"))
            .expect(1)
            .mount(&mock_server)
            .await;

        let config = HttpConfig {
            max_retries: 2,
            retry_delay: Duration::from_millis(10),
            ..Default::default()
        };
        let client = HttpClient::with_config(config);
        let result = client.get(&format!("{}/retry", &mock_server.uri())).await;
        assert_eq!(result.unwrap(), "recovered");
    }
}
