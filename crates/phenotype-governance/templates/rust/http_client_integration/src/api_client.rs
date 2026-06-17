//! HTTP API Client
//!
//! Example of using phenotype-http-client for API calls.

use phenotype_http_client::{ReqwestAdapter, HttpClientPort, MockAdapter, Response};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ApiError {
    #[error("HTTP error: {0}")]
    Http(String),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: String,
}

/// API client using phenotype-http-client
pub struct ApiClient {
    http: ReqwestAdapter,
    base_url: String,
}

impl ApiClient {
    /// Create a new API client
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            http: ReqwestAdapter::new(),
            base_url: base_url.into(),
        }
    }

    /// Get a user by ID
    pub async fn get_user(&self, id: u64) -> Result<User, ApiError> {
        let url = format!("{}/users/{}", self.base_url, id);
        let response = self.http.get(&url).await
            .map_err(|e| ApiError::Http(e.to_string()))?;
        
        if !response.is_success() {
            return Err(ApiError::Http(format!("Status: {}", response.status)));
        }
        
        let user: User = response.json()
            .map_err(|e| ApiError::Json(e))?;
        
        Ok(user)
    }

    /// Create a new user
    pub async fn create_user(&self, name: &str, email: &str) -> Result<User, ApiError> {
        let url = format!("{}/users", self.base_url);
        let body = serde_json::json!({
            "name": name,
            "email": email
        });
        
        let request = phenotype_http_client::Request::builder()
            .method(phenotype_http_client::Method::POST)
            .uri(&url)
            .header("Content-Type", "application/json")
            .body(body.to_string().as_bytes())
            .build()
            .map_err(|e| ApiError::Http(e.to_string()))?;
        
        let response = self.http.execute(request).await
            .map_err(|e| ApiError::Http(e.to_string()))?;
        
        if !response.is_success() {
            return Err(ApiError::Http(format!("Status: {}", response.status)));
        }
        
        let user: User = response.json()
            .map_err(|e| ApiError::Json(e))?;
        
        Ok(user)
    }
}

/// Testing with MockAdapter
#[cfg(test)]
pub mod tests {
    use super::*;

    #[tokio::test]
    async fn test_mock_client() {
        let mock = MockAdapter::new();
        
        // Configure mock response
        mock.when("https://api.example.com/users/1")
            .then_return_json(&serde_json::json!({
                "id": 1,
                "name": "Test User",
                "email": "test@example.com"
            })).unwrap();
        
        // Make request
        let response = mock.get("https://api.example.com/users/1").await.unwrap();
        
        // Verify
        assert!(response.is_success());
        assert!(mock.was_requested("https://api.example.com/users/1"));
        
        let user: User = response.json().unwrap();
        assert_eq!(user.id, 1);
        assert_eq!(user.name, "Test User");
    }
}
