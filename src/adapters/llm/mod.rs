//! LLM adapters - Implementations of the [`LLM`] port.
//!
//! Two adapters are provided today:
//!
//! * [`EchoLLM`] - a deterministic stub useful for tests and offline runs.
//!   It returns a short echo of the input without making any network calls.
//! * [`OpenAIChatLLM`] - an `OpenAI` Chat Completions client. Activated by the
//!   `openai` cargo feature (pulls in `reqwest`). The context is serialized
//!   as a `[system, user]` pair, where the system message summarizes the
//!   memory entries and tool calls, and the user message is the `Context::input`.
//!
//! All adapters are `Send + Sync` and implement [`LLM`] from
//! `crate::domain::ports`.

use async_trait::async_trait;
#[cfg(feature = "openai")]
use serde::{Deserialize, Serialize};

use crate::domain::ports::{GenerationResult, LLM};
use crate::domain::{Context, Result};

/// Adapter that returns a deterministic echo of the prompt.
///
/// Useful for:
/// * Unit tests of the agent loop without network.
/// * CI / offline builds.
/// * Smoke-checking tool wiring.
#[derive(Debug, Default, Clone)]
pub struct EchoLLM {
    prefix: Option<String>,
}

impl EchoLLM {
    /// Create a bare echo adapter.
    pub fn new() -> Self {
        Self { prefix: None }
    }

    /// Prefix every response (handy for tagging in logs).
    pub fn with_prefix(prefix: impl Into<String>) -> Self {
        Self {
            prefix: Some(prefix.into()),
        }
    }
}

#[async_trait]
impl LLM for EchoLLM {
    async fn complete(&self, prompt: &str) -> Result<String> {
        Ok(self
            .prefix
            .as_ref()
            .map_or_else(|| prompt.to_string(), |prefix| format!("{prefix}{prompt}")))
    }

    async fn generate(&self, context: &Context) -> Result<String> {
        self.complete(&context.input).await
    }

    async fn generate_with_tools(
        &self,
        context: &Context,
        _tools: Vec<serde_json::Value>,
    ) -> Result<GenerationResult> {
        let text = self.generate(context).await?;
        Ok(GenerationResult::text(text))
    }
}

/// OpenAI Chat Completions adapter. Activated by the `openai` cargo feature.
#[cfg(feature = "openai")]
#[derive(Debug, Clone)]
pub struct OpenAIChatLLM {
    api_key: String,
    model: String,
    base_url: String,
    client: reqwest::Client,
}

#[cfg(feature = "openai")]
impl OpenAIChatLLM {
    /// Build an adapter from the `OPENAI_API_KEY` env var. Returns `None` if missing.
    pub fn from_env() -> Option<Self> {
        let api_key = std::env::var("OPENAI_API_KEY").ok()?;
        Some(Self::with_api_key(api_key))
    }

    /// Build an adapter with an explicit API key. Defaults to `gpt-4o-mini`.
    pub fn with_api_key(api_key: impl Into<String>) -> Self {
        Self {
            api_key: api_key.into(),
            model: "gpt-4o-mini".to_string(),
            base_url: "https://api.openai.com/v1".to_string(),
            client: reqwest::Client::new(),
        }
    }

    /// Override the model.
    pub fn model(mut self, model: impl Into<String>) -> Self {
        self.model = model.into();
        self
    }

    /// Override the base URL (Azure OpenAI, vLLM, local, etc.).
    pub fn base_url(mut self, base_url: impl Into<String>) -> Self {
        self.base_url = base_url.into();
        self
    }

    /// Serialize a [`Context`] into the (system, user) message pair that
    /// the Chat Completions API expects.
    fn render_context(context: &Context) -> (String, String) {
        let memory_summary = if context.memory.is_empty() {
            String::new()
        } else {
            let entries: Vec<String> = context
                .memory
                .iter()
                .map(|e| format!("[{:?}] {}", e.role, e.content))
                .collect();
            format!("Recent memory:\n{}", entries.join("\n"))
        };
        let tool_summary = if context.tool_calls.is_empty() {
            String::new()
        } else {
            let calls: Vec<String> = context
                .tool_calls
                .iter()
                .map(|c| format!("- {} ({})", c.name, c.id))
                .collect();
            format!("Tool calls made:\n{}", calls.join("\n"))
        };
        let mut system_parts: Vec<&str> = Vec::new();
        if !memory_summary.is_empty() {
            system_parts.push(&memory_summary);
        }
        if !tool_summary.is_empty() {
            system_parts.push(&tool_summary);
        }
        let system = system_parts.join("\n\n");
        (system, context.input.clone())
    }

    async fn post_chat(
        &self,
        messages: Vec<ChatMessage<'_>>,
        tools: Vec<serde_json::Value>,
    ) -> Result<ChatResponse> {
        let body = ChatRequest {
            model: &self.model,
            messages,
            tools,
        };
        let url = format!("{}/chat/completions", self.base_url);
        let resp = self
            .client
            .post(&url)
            .bearer_auth(&self.api_key)
            .json(&body)
            .send()
            .await
            .map_err(|e| crate::domain::Error::LLM(format!("http: {e}")))?;
        if !resp.status().is_success() {
            let status = resp.status();
            let body = resp.text().await.unwrap_or_default();
            return Err(crate::domain::Error::LLM(format!(
                "openai {status}: {body}"
            )));
        }
        resp.json()
            .await
            .map_err(|e| crate::domain::Error::LLM(format!("decode: {e}")))
    }
}

#[cfg(feature = "openai")]
#[derive(Debug, Serialize)]
struct ChatRequest<'a> {
    model: &'a str,
    messages: Vec<ChatMessage<'a>>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    tools: Vec<serde_json::Value>,
}

#[cfg(feature = "openai")]
#[derive(Debug, Serialize)]
struct ChatMessage<'a> {
    role: &'a str,
    content: &'a str,
}

#[cfg(feature = "openai")]
#[derive(Debug, Deserialize)]
struct ChatResponse {
    choices: Vec<ChatChoice>,
}

#[cfg(feature = "openai")]
#[derive(Debug, Deserialize)]
struct ChatChoice {
    message: ChatResponseMessage,
}

#[cfg(feature = "openai")]
#[derive(Debug, Deserialize)]
struct ChatResponseMessage {
    content: Option<String>,
    tool_calls: Option<Vec<ChatToolCall>>,
}

#[cfg(feature = "openai")]
#[derive(Debug, Deserialize)]
struct ChatToolCall {
    id: String,
    #[serde(rename = "type")]
    #[allow(dead_code)]
    kind: String,
    function: ChatToolCallFunction,
}

#[cfg(feature = "openai")]
#[derive(Debug, Deserialize)]
struct ChatToolCallFunction {
    name: String,
    arguments: String,
}

#[cfg(feature = "openai")]
#[async_trait]
impl LLM for OpenAIChatLLM {
    async fn complete(&self, prompt: &str) -> Result<String> {
        let parsed = self
            .post_chat(
                vec![ChatMessage {
                    role: "user",
                    content: prompt,
                }],
                Vec::new(),
            )
            .await?;
        parsed
            .choices
            .into_iter()
            .next()
            .and_then(|c| c.message.content)
            .ok_or_else(|| crate::domain::Error::LLM("no choices returned".into()))
    }

    async fn generate(&self, context: &Context) -> Result<String> {
        let (system, user) = Self::render_context(context);
        let mut messages = Vec::new();
        if !system.is_empty() {
            messages.push(ChatMessage {
                role: "system",
                content: &system,
            });
        }
        messages.push(ChatMessage {
            role: "user",
            content: &user,
        });
        let parsed = self.post_chat(messages, Vec::new()).await?;
        parsed
            .choices
            .into_iter()
            .next()
            .and_then(|c| c.message.content)
            .ok_or_else(|| crate::domain::Error::LLM("no choices returned".into()))
    }

    async fn generate_with_tools(
        &self,
        context: &Context,
        tools: Vec<serde_json::Value>,
    ) -> Result<GenerationResult> {
        let (system, user) = Self::render_context(context);
        let mut messages = Vec::new();
        if !system.is_empty() {
            messages.push(ChatMessage {
                role: "system",
                content: &system,
            });
        }
        messages.push(ChatMessage {
            role: "user",
            content: &user,
        });
        let parsed = self.post_chat(messages, tools).await?;
        let choice = parsed
            .choices
            .into_iter()
            .next()
            .ok_or_else(|| crate::domain::Error::LLM("no choices returned".into()))?;
        let tool_calls = choice
            .message
            .tool_calls
            .unwrap_or_default()
            .into_iter()
            .map(|tc| {
                let params: serde_json::Value =
                    serde_json::from_str(&tc.function.arguments).unwrap_or(serde_json::json!({}));
                crate::domain::ToolCall {
                    id: tc.id,
                    name: tc.function.name,
                    params,
                }
            })
            .collect();
        Ok(GenerationResult::with_tools(
            choice.message.content,
            tool_calls,
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn echo_returns_prompt() {
        let llm = EchoLLM::new();
        let out = llm.complete("ping").await.unwrap();
        assert_eq!(out, "ping");
    }

    #[tokio::test]
    async fn echo_with_prefix() {
        let llm = EchoLLM::with_prefix("[echo] ");
        let out = llm.complete("ping").await.unwrap();
        assert_eq!(out, "[echo] ping");
    }

    #[tokio::test]
    async fn echo_generate_uses_context_input() {
        let llm = EchoLLM::new();
        let ctx = Context::new("hi there");
        let out = llm.generate(&ctx).await.unwrap();
        assert_eq!(out, "hi there");
    }
}
