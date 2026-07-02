//! Domain errors

use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("Agent error: {0}")]
    Agent(String),

    #[error("Skill error: {0}")]
    Skill(String),

    #[error("Tool error: {0}")]
    Tool(String),

    #[error("Memory error: {0}")]
    Memory(String),

    #[error("LLM error: {0}")]
    LLM(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Execution error: {0}")]
    Execution(String),
}

pub type Result<T> = std::result::Result<T, Error>;

/// User-facing error envelope emitted by the CLI in JSON mode and by any
/// HTTP/RPC layer that wraps the crate (L14, L36).
///
/// The envelope is intentionally flat: `code`, `message`, and an optional
/// `cause` chain. Callers can match on `code` programmatically without
/// parsing free-form strings, and `message` stays safe to surface to a
/// human user.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ErrorEnvelope {
    /// Stable, machine-readable identifier (e.g. `"agent"`, `"tool"`,
    /// `"config"`). Matches the variant name of [`Error`] so automation
    /// can route on it.
    pub code: String,
    /// Human-readable description. Safe to print to stderr/stdout.
    pub message: String,
    /// Optional chain of inner causes, most-recent first.
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub cause: Vec<String>,
}

impl ErrorEnvelope {
    /// Build an envelope from a domain [`Error`].
    pub fn from_error(err: &Error) -> Self {
        let code = match err {
            Error::Agent(_) => "agent",
            Error::Skill(_) => "skill",
            Error::Tool(_) => "tool",
            Error::Memory(_) => "memory",
            Error::LLM(_) => "llm",
            Error::Config(_) => "config",
            Error::Execution(_) => "execution",
        };
        Self {
            code: code.to_string(),
            message: err.to_string(),
            cause: Vec::new(),
        }
    }

    /// Render the envelope as a single-line JSON string. Falls back to a
    /// minimal hand-rolled formatter if `serde_json` is unavailable so the
    /// CLI never panics when emitting an error.
    pub fn to_json(&self) -> String {
        serde_json::to_string(self).unwrap_or_else(|_| {
            format!(
                "{{\"code\":{},\"message\":{}}}",
                json_string(&self.code),
                json_string(&self.message),
            )
        })
    }
}

impl std::fmt::Display for ErrorEnvelope {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[{}] {}", self.code, self.message)
    }
}

impl std::error::Error for ErrorEnvelope {}

fn json_string(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn envelope_from_error_carries_variant_code() {
        let err = Error::Tool("boom".into());
        let env = ErrorEnvelope::from_error(&err);
        assert_eq!(env.code, "tool");
        assert!(env.message.contains("boom"));
        assert!(env.cause.is_empty());
    }

    #[test]
    fn envelope_json_round_trip() {
        let mut env = ErrorEnvelope::from_error(&Error::Config("missing key".into()));
        env.cause.push("inner: bad path".into());
        let json = env.to_json();
        let parsed: ErrorEnvelope = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.code, "config");
        assert_eq!(parsed.message, env.message);
        assert_eq!(parsed.cause, vec!["inner: bad path".to_string()]);
    }

    #[test]
    fn envelope_display_is_human_readable() {
        let env = ErrorEnvelope::from_error(&Error::Agent("nope".into()));
        let s = format!("{env}");
        assert_eq!(s, "[agent] Agent error: nope");
    }
}
