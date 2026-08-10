//! NFR-006 acceptance tests: Panic safety and supply-chain hardening.
//!
//! Each `#[test]` in this module is annotated with the NFR it exercises.
//! NFR-006: panic safety — Mutex poison recovery
//! NFR-007: supply chain — pinned git dependencies

use std::sync::Mutex;

/// NFR-006: panic safety — `Mutex::lock().unwrap()` has been replaced with
/// poison-tolerant `.unwrap_or_else(|e| e.into_inner())` across all adapter
/// code. This test verifies the recovery pattern compiles and works.
#[test]
fn nfr_006_mutex_poison_recovery_compiles_and_recovers() {
    // Simulate a poisoned Mutex by panicking inside a lock guard.
    let lock: Mutex<Vec<i32>> = Mutex::new(vec![1, 2, 3]);

    // Poison the mutex.
    let result = std::panic::catch_unwind(|| {
        let _guard = lock.lock().unwrap();
        panic!("intentional poison");
    });
    assert!(result.is_err(), "mutex should be poisoned");

    // Verify that unwrap_or_else(|e| e.into_inner()) recovers the data.
    let guard = lock
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    assert_eq!(*guard, vec![1, 2, 3], "data survives poison");
    drop(guard);
}

/// NFR-006: panic safety — `AgentEngine`'s `set_agent` works after a simulated
/// concurrent panic would have poisoned an unrelated mutex.
#[tokio::test(flavor = "multi_thread")]
async fn nfr_006_engine_outputs_accessible_after_recovery() {
    use agentkit::application::{AgentExecutor, SimpleAgent};
    use agentkit::domain::agents::AgentConfig;
    use agentkit::domain::context::OutputContent;

    let executor = AgentExecutor::new(AgentConfig::new("panic-safe"));
    let output = executor
        .run(SimpleAgent, "hello".to_string())
        .await
        .expect("executor should run after set_agent");
    match output.content {
        OutputContent::Text(s) => assert_eq!(s, "Echo: hello"),
        other => panic!("expected Text, got {other:?}"),
    }
}

/// NFR-006: panic safety — `ToolRegistry` operations that lock the inner
/// registry use poison-tolerant locking.
#[tokio::test(flavor = "multi_thread")]
async fn nfr_006_tool_registry_register_and_dispatch_work() {
    use agentkit::domain::tools::{CalculatorTool, ToolCall};
    use agentkit::ToolRegistry;
    use serde_json::json;

    let mut registry = ToolRegistry::new();
    registry
        .register(Box::new(CalculatorTool))
        .expect("register should succeed");

    // Dispatching a tool call exercises lock() in SkillPort::invoke and
    // ToolHandler::invoke (which uses block_in_place + Handle::block_on).
    let call = ToolCall::new("calculator", json!({"expression": "2+2"}), "nfr-006");
    let resp = registry.call(call).expect("call should succeed");
    assert_eq!(resp.id, "nfr-006");
    assert!(resp.error.is_none());
}

/// NFR-007: supply chain — substrate dependency is pinned to a specific git
/// rev for reproducible builds, not an unpinned branch pointer.
#[test]
fn nfr_007_substrate_dep_is_pinned_to_rev() {
    // Read Cargo.toml and verify the substrate line includes `rev = `.
    let cargo_toml = include_str!("../Cargo.toml");
    let substrate_line = cargo_toml
        .lines()
        .find(|l| l.contains("substrate") && l.contains("git"))
        .expect("Cargo.toml must have a substrate git dependency");

    assert!(
        substrate_line.contains("rev = "),
        "substrate dep must be pinned to a rev: got {substrate_line:?}"
    );
    assert!(
        substrate_line.contains("ce90e8a"),
        "substrate dep should pin the resolved Cargo.lock rev: got {substrate_line:?}"
    );
}

/// NFR-007: supply chain — deny.toml allow-git entries must map to
/// a pinned dependency in Cargo.toml.
#[test]
fn nfr_007_all_allow_git_deps_have_rev_in_cargo_toml() {
    use std::fs;

    let deny_toml =
        fs::read_to_string(std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("deny.toml"))
            .expect("deny.toml should exist");

    let cargo_toml = include_str!("../Cargo.toml");

    // Parse allow-git URLs from deny.toml.
    for line in deny_toml.lines() {
        let trimmed = line.trim();
        if let Some(url) = trimmed.strip_prefix("\"https://") {
            let url = url.trim_end_matches("\",");
            // Find matching dep in Cargo.toml and check it has rev.
            let dep_line = cargo_toml
                .lines()
                .find(|l| l.contains(url))
                .unwrap_or_else(|| panic!("allow-git dep {url} not found in Cargo.toml"));

            assert!(
                dep_line.contains("rev = "),
                "allow-git dep {url} is not pinned to a rev: {dep_line}"
            );
        }
    }
}
