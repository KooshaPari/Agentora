//! Example of testing with MockAdapter

use phenotype_http_client::{MockAdapter, HttpClientPort};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct ApiResponse {
    status: String,
    data: serde_json::Value,
}

#[tokio::test]
async fn test_mock_get_request() {
    let mock = MockAdapter::new();
    
    // Configure mock
    mock.when("https://api.example.com/data")
        .then_return_json(&serde_json::json!({
            "status": "ok",
            "data": { "value": 42 }
        })).unwrap();
    
    // Execute
    let response = mock.get("https://api.example.com/data").await.unwrap();
    
    // Verify
    assert!(response.is_success());
    assert!(mock.was_requested("https://api.example.com/data"));
    
    let body: ApiResponse = response.json().unwrap();
    assert_eq!(body.status, "ok");
}

#[tokio::test]
async fn test_mock_error_response() {
    let mock = MockAdapter::new();
    
    // Configure error response
    mock.when("https://api.example.com/error")
        .then_return_error(500, "Internal Server Error");
    
    let response = mock.get("https://api.example.com/error").await.unwrap();
    
    assert!(!response.is_success());
    assert_eq!(response.status, 500);
}

#[tokio::test]
async fn test_multiple_endpoints() {
    let mock = MockAdapter::new();
    
    // Configure multiple endpoints
    mock.when("https://api.example.com/users")
        .then_return_json(&serde_json::json!([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ])).unwrap();
    
    mock.when("https://api.example.com/posts")
        .then_return_json(&serde_json::json!([
            {"id": 1, "title": "First Post"}
        ])).unwrap();
    
    // Test both
    let users = mock.get("https://api.example.com/users").await.unwrap();
    let posts = mock.get("https://api.example.com/posts").await.unwrap();
    
    assert!(users.is_success());
    assert!(posts.is_success());
    
    // Verify request count
    assert_eq!(mock.request_count(), 2);
}

#[tokio::test]
async fn test_mock_verification() {
    let mock = MockAdapter::new();
    
    // Configure
    mock.when("https://api.example.com/api")
        .then_return_json(&serde_json::json!({"status": "ok"})).unwrap();
    
    // Make request
    let _ = mock.get("https://api.example.com/api").await;
    
    // Verify specific request was made
    assert!(mock.was_requested("https://api.example.com/api"));
    
    // Verify request count
    assert_eq!(mock.request_count(), 1);
    
    // Clear and verify reset
    mock.clear();
    assert_eq!(mock.request_count(), 0);
}
