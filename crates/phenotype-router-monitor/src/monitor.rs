use thiserror::Error;

#[derive(Error, Debug)]
pub enum MonitorServiceError {
    #[error("Router not found: {0}")]
    RouterNotFound(String),
    #[error("Connection failed: {0}")]
    ConnectionFailed(String),
    #[error("Timeout: {0}")]
    Timeout(String),
}

pub type MonitorServiceResult<T> = Result<T, MonitorServiceError>;

pub struct RouterMonitorService {
    pub name: String,
    pub version: String,
}

impl RouterMonitorService {
    pub fn new(name: String, version: String) -> Self {
        Self { name, version }
    }

    pub fn service_name(&self) -> &str {
        &self.name
    }

    pub fn service_version(&self) -> &str {
        &self.version
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_service_creation() {
        let service = RouterMonitorService::new("router-monitor".into(), "1.0.0".into());
        assert_eq!(service.service_name(), "router-monitor");
        assert_eq!(service.service_version(), "1.0.0");
    }
}
