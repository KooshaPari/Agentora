use async_trait::async_trait;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use url::Url;

#[derive(Error, Debug)]
pub enum MonitorError {
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("URL parse error: {0}")]
    Url(#[from] url::ParseError),
    #[error("API error: {status} - {message}")]
    Api { status: u16, message: String },
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

pub type MonitorResult<T> = Result<T, MonitorError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterMetrics {
    pub router_id: String,
    pub uptime_seconds: u64,
    pub requests_total: u64,
    pub requests_per_second: f64,
    pub avg_latency_ms: f64,
    pub error_rate: f64,
    pub active_connections: u32,
    pub memory_usage_bytes: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterStatus {
    pub router_id: String,
    pub healthy: bool,
    pub last_check: String,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub routers: Vec<RouterStatus>,
}

pub struct RouterMonitorClient {
    client: Client,
    base_url: Url,
}

impl RouterMonitorClient {
    pub fn new(base_url: &str) -> MonitorResult<Self> {
        Ok(Self {
            client: Client::new(),
            base_url: Url::parse(base_url)?,
        })
    }

    pub async fn get_metrics(&self, router_id: &str) -> MonitorResult<RouterMetrics> {
        let url = self.base_url.join(&format!("/api/v1/routers/{}/metrics", router_id))?;
        let response = self.client.get(url).send().await?;
        
        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }

    pub async fn get_all_metrics(&self) -> MonitorResult<Vec<RouterMetrics>> {
        let url = self.base_url.join("/api/v1/routers/metrics")?;
        let response = self.client.get(url).send().await?;
        
        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }

    pub async fn get_status(&self, router_id: &str) -> MonitorResult<RouterStatus> {
        let url = self.base_url.join(&format!("/api/v1/routers/{}/status", router_id))?;
        let response = self.client.get(url).send().await?;
        
        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }

    pub async fn get_health(&self) -> MonitorResult<HealthResponse> {
        let url = self.base_url.join("/api/v1/health")?;
        let response = self.client.get(url).send().await?;
        
        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }
}

#[async_trait]
pub trait RouterMetricsProvider: Send + Sync {
    async fn fetch_metrics(&self, router_id: &str) -> MonitorResult<RouterMetrics>;
    async fn fetch_all_metrics(&self) -> MonitorResult<Vec<RouterMetrics>>;
    async fn check_health(&self) -> MonitorResult<HealthResponse>;
}

#[async_trait]
impl RouterMetricsProvider for RouterMonitorClient {
    async fn fetch_metrics(&self, router_id: &str) -> MonitorResult<RouterMetrics> {
        self.get_metrics(router_id).await
    }

    async fn fetch_all_metrics(&self) -> MonitorResult<Vec<RouterMetrics>> {
        self.get_all_metrics().await
    }

    async fn check_health(&self) -> MonitorResult<HealthResponse> {
        self.get_health().await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_router_metrics_serialization() {
        let json = r#"{
            "router_id": "router-1",
            "uptime_seconds": 3600,
            "requests_total": 10000,
            "requests_per_second": 2.78,
            "avg_latency_ms": 15.5,
            "error_rate": 0.01,
            "active_connections": 42,
            "memory_usage_bytes": 1073741824
        }"#;
        let metrics: RouterMetrics = serde_json::from_str(json).unwrap();
        assert_eq!(metrics.router_id, "router-1");
        assert_eq!(metrics.requests_total, 10000);
    }

    #[test]
    fn test_router_status_serialization() {
        let json = r#"{
            "router_id": "router-1",
            "healthy": true,
            "last_check": "2026-03-30T12:00:00Z",
            "version": "1.0.0"
        }"#;
        let status: RouterStatus = serde_json::from_str(json).unwrap();
        assert!(status.healthy);
        assert_eq!(status.version, "1.0.0");
    }

    #[test]
    fn test_client_creation() {
        let client = RouterMonitorClient::new("http://localhost:8080").unwrap();
        assert_eq!(client.base_url.as_str(), "http://localhost:8080/");
    }

    #[test]
    fn test_invalid_url() {
        let result = RouterMonitorClient::new("not-a-valid-url");
        assert!(result.is_err());
    }
}
