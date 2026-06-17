use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use crate::error::{ForgecodeError, Result};

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct LLMRequest {
    pub model: String,
    pub prompt: String,
    pub max_tokens: Option<u32>,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct TokenUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct LLMResponse {
    pub text: String,
    pub usage: TokenUsage,
}

#[async_trait]
pub trait CustomProvider: Send + Sync {
    async fn call(&self, request: &LLMRequest) -> Result<LLMResponse>;
}

pub struct ProviderRegistry {
    providers: RwLock<HashMap<String, Arc<dyn CustomProvider>>>,
}

impl Default for ProviderRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl ProviderRegistry {
    pub fn new() -> Self {
        Self {
            providers: RwLock::new(HashMap::new()),
        }
    }

    pub fn register<P: CustomProvider + 'static>(&self, id: String, provider: P) -> Result<()> {
        let mut providers = self
            .providers
            .write()
            .map_err(|_| ForgecodeError::InvalidConfig("lock poisoned".into()))?;
        providers.insert(id, Arc::new(provider));
        Ok(())
    }

    pub fn get(&self, id: &str) -> Option<Arc<dyn CustomProvider>> {
        let providers = self.providers.read().ok()?;
        providers.get(id).cloned()
    }

    pub fn list_ids(&self) -> Vec<String> {
        self.providers
            .read()
            .map(|p| p.keys().cloned().collect())
            .unwrap_or_default()
    }

    pub async fn call(&self, id: &str, request: &LLMRequest) -> Result<LLMResponse> {
        let provider = self
            .get(id)
            .ok_or_else(|| ForgecodeError::ProviderNotFound(id.into()))?;
        provider.call(request).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockProvider {
        response_text: String,
        input_tokens: u32,
        output_tokens: u32,
    }

    impl MockProvider {
        fn new(text: impl Into<String>, input: u32, output: u32) -> Self {
            Self {
                response_text: text.into(),
                input_tokens: input,
                output_tokens: output,
            }
        }
    }

    #[async_trait]
    impl CustomProvider for MockProvider {
        async fn call(&self, _request: &LLMRequest) -> Result<LLMResponse> {
            Ok(LLMResponse {
                text: self.response_text.clone(),
                usage: TokenUsage {
                    input_tokens: self.input_tokens,
                    output_tokens: self.output_tokens,
                },
            })
        }
    }

    #[tokio::test]
    async fn test_register_and_get_provider() {
        let registry = ProviderRegistry::new();
        registry
            .register("test".into(), MockProvider::new("hello", 10, 5))
            .unwrap();

        let provider = registry.get("test");
        assert!(provider.is_some());

        let ids = registry.list_ids();
        assert_eq!(ids, vec!["test"]);
    }

    #[tokio::test]
    async fn test_call_provider() {
        let registry = ProviderRegistry::new();
        registry
            .register("mock".into(), MockProvider::new("response", 10, 20))
            .unwrap();

        let request = LLMRequest {
            model: "gpt-4".into(),
            prompt: "hello".into(),
            max_tokens: Some(100),
        };

        let response = registry.call("mock", &request).await.unwrap();
        assert_eq!(response.text, "response");
        assert_eq!(response.usage.input_tokens, 10);
        assert_eq!(response.usage.output_tokens, 20);
    }

    #[tokio::test]
    async fn test_provider_not_found() {
        let registry = ProviderRegistry::new();
        let request = LLMRequest {
            model: "gpt-4".into(),
            prompt: "hello".into(),
            max_tokens: None,
        };

        let result = registry.call("nonexistent", &request).await;
        assert!(matches!(result, Err(ForgecodeError::ProviderNotFound(_))));
    }

    #[tokio::test]
    async fn test_multiple_providers() {
        let registry = ProviderRegistry::new();
        registry
            .register("p1".into(), MockProvider::new("one", 1, 1))
            .unwrap();
        registry
            .register("p2".into(), MockProvider::new("two", 2, 2))
            .unwrap();

        let ids = registry.list_ids();
        assert!(ids.contains(&"p1".into()));
        assert!(ids.contains(&"p2".into()));
        assert_eq!(ids.len(), 2);
    }

    #[tokio::test]
    async fn test_llm_request_serialization() {
        let request = LLMRequest {
            model: "gpt-4".into(),
            prompt: "test prompt".into(),
            max_tokens: Some(500),
        };

        let json = serde_json::to_string(&request).unwrap();
        let parsed: LLMRequest = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.model, "gpt-4");
        assert_eq!(parsed.prompt, "test prompt");
        assert_eq!(parsed.max_tokens, Some(500));
    }

    #[tokio::test]
    async fn test_llm_response_serialization() {
        let response = LLMResponse {
            text: "generated text".into(),
            usage: TokenUsage {
                input_tokens: 100,
                output_tokens: 50,
            },
        };

        let json = serde_json::to_string(&response).unwrap();
        let parsed: LLMResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.text, "generated text");
        assert_eq!(parsed.usage.input_tokens, 100);
    }

    #[tokio::test]
    async fn test_empty_registry() {
        let registry = ProviderRegistry::new();
        assert!(registry.list_ids().is_empty());
        assert!(registry.get("anything").is_none());
    }

    #[tokio::test]
    async fn test_overwrite_provider() {
        let registry = ProviderRegistry::new();
        registry
            .register("same".into(), MockProvider::new("first", 1, 1))
            .unwrap();
        registry
            .register("same".into(), MockProvider::new("second", 2, 2))
            .unwrap();

        let ids = registry.list_ids();
        assert_eq!(ids.len(), 1);
    }
}
