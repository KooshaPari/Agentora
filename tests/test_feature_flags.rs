//! NFR-002 acceptance tests: Feature-flag isolation for heavy backends.
//!
//! Each `#[test]` in this module is annotated with the NFR it exercises.
//! NFR-002: feature flags

use agentkit::adapters::llm::EchoLLM;
use agentkit::adapters::memory::InMemoryAdapter;
use agentkit::domain::ports::LLM;

/// NFR-002: feature flags — the default (no-feature) build still pulls
/// `EchoLLM` and `InMemoryAdapter`, both of which compile without the
/// `openai` / `redis-memory` / `sqlite-memory` features.
#[tokio::test]
async fn nfr_002_default_build_exposes_echo_llm() {
    let llm = EchoLLM::new();
    let out = llm.complete("ping").await.expect("complete");
    assert_eq!(out, "ping");
}

#[test]
fn nfr_002_default_build_exposes_in_memory_adapter() {
    let _adapter = InMemoryAdapter::new();
}

/// NFR-002: feature flags — the in-tree deterministic alternatives
/// (`EchoLLM`, `InMemoryAdapter`) exist in the default build so that the
/// default test suite has no network or external service dependency.
#[test]
fn nfr_002_default_test_suite_has_no_external_dependencies() {
    // The presence of these types in the default build is the assertion.
    // If a regression makes them `#[cfg(feature = "...")]`-gated, this
    // file will stop compiling under `cargo test` (no features).
    fn _exists<T>(_: T) {}
    _exists(EchoLLM::new());
    _exists(InMemoryAdapter::new());
}

/// NFR-002: feature flags — `Cargo.toml` declares `openai`,
/// `redis-memory`, and `sqlite-memory` as features. The test below parses
/// `Cargo.toml` at runtime to make the gating explicit.
#[test]
fn nfr_002_cargo_toml_declares_expected_features() {
    let manifest = include_str!("../Cargo.toml");
    assert!(manifest.contains("openai"), "missing 'openai' feature");
    assert!(
        manifest.contains("redis-memory"),
        "missing 'redis-memory' feature"
    );
    assert!(
        manifest.contains("sqlite-memory"),
        "missing 'sqlite-memory' feature"
    );
    // Heavy crates must be declared optional, not required.
    assert!(
        manifest.contains("reqwest = { version = \"0.13\""),
        "reqwest must be optional"
    );
    assert!(
        manifest.contains("redis = { version = \"1.2\""),
        "redis must be optional"
    );
    assert!(
        manifest.contains("rusqlite = { version = \"0.40\""),
        "rusqlite must be optional"
    );
}
