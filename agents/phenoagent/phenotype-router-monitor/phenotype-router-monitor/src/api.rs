use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiVersion {
    pub version: String,
    pub build_date: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiInfo {
    pub service: String,
    pub version: ApiVersion,
    pub endpoints: Vec<String>,
}

impl ApiInfo {
    pub fn new(service: String, version: String) -> Self {
        Self {
            service,
            version: ApiVersion {
                version,
                build_date: chrono::Utc::now().to_rfc3339(),
            },
            endpoints: vec![
                "/api/v1/routers/{id}/metrics".into(),
                "/api/v1/routers/metrics".into(),
                "/api/v1/routers/{id}/status".into(),
                "/api/v1/health".into(),
            ],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_api_info_creation() {
        let info = ApiInfo::new("router-monitor".into(), "1.0.0".into());
        assert_eq!(info.service, "router-monitor");
        assert_eq!(info.endpoints.len(), 4);
    }
}
