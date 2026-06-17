//! NFR-003 acceptance tests: Deterministic in-tree test surface.
//!
//! Each `#[test]` in this module is annotated with the NFR it exercises.
//! NFR-003: deterministic surface

use agentkit::adapters::llm::EchoLLM;
use agentkit::adapters::memory::InMemoryAdapter;
use agentkit::domain::memory::{InMemoryStore, MemoryEntry, MemoryStore};
use agentkit::domain::ports::{MemoryPort, LLM};

/// NFR-003: deterministic surface — `EchoLLM` is fully deterministic and
/// carries per-instance state via `with_prefix`.
#[tokio::test]
async fn nfr_003_echo_llm_deterministic() {
    let a = EchoLLM::new();
    let b = EchoLLM::with_prefix("x:");
    assert_eq!(a.complete("p").await.unwrap(), "p");
    assert_eq!(
        a.complete("p").await.unwrap(),
        a.complete("p").await.unwrap()
    );
    assert_eq!(b.complete("p").await.unwrap(), "x:p");
}

/// NFR-003: deterministic surface — `InMemoryStore` save / search / clear
/// are pure in-memory operations.
#[test]
fn nfr_003_in_memory_store_is_pure() {
    let mut store = InMemoryStore::new();
    store.save(&MemoryEntry::user("alpha")).expect("save");
    let hits = store.search("alpha", 10).expect("search");
    assert_eq!(hits.len(), 1);
    store.clear().expect("clear");
    assert!(store.search("alpha", 10).expect("search").is_empty());
}

/// NFR-003: deterministic surface — `InMemoryAdapter` is thread-safe and
/// stays consistent across many adds / reads.
#[test]
fn nfr_003_in_memory_adapter_is_consistent() {
    let adapter = InMemoryAdapter::new();
    for i in 0..50 {
        adapter
            .add(MemoryEntry::user(format!("msg-{i}")))
            .expect("add");
    }
    let recent = adapter.recent(100).expect("recent");
    assert_eq!(recent.len(), 50);
    let hits = adapter.search("msg-1").expect("search");
    // "msg-1", "msg-10".."msg-19" all contain "msg-1".
    assert!(!hits.is_empty());
}

/// NFR-003: deterministic surface — `EchoLLM` does not panic on empty or
/// unicode input.
#[tokio::test]
async fn nfr_003_echo_llm_handles_edge_inputs() {
    let llm = EchoLLM::new();
    assert_eq!(llm.complete("").await.unwrap(), "");
    assert_eq!(llm.complete("🦀").await.unwrap(), "🦀");
    assert_eq!(llm.complete("\n\t\r").await.unwrap(), "\n\t\r");
}
