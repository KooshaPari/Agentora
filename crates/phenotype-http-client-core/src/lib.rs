//! HTTP client core library

pub struct HttpClient;

impl HttpClient {
    pub fn new() -> Self {
        Self
    }
}

impl Default for HttpClient {
    fn default() -> Self {
        Self::new()
    }
}
