//! FR-004 acceptance tests: Two-tier memory — short-term ring buffer plus
//! long-term store.
//!
//! Each `#[test]` in this module is annotated with the FR it exercises.
//! FR-004: memory tiers

use agentkit::domain::memory::{
    InMemoryStore, LongTermMemory, MemoryEntry, MemoryRole, MemoryStore, ShortTermMemory,
};

/// FR-004: memory tiers — `ShortTermMemory` is a ring buffer: when its
/// limit is reached, the oldest entry is evicted.
#[test]
fn fr_004_short_term_evicts_oldest_at_limit() {
    let mut memory = ShortTermMemory::new(2);
    memory.add(MemoryEntry::user("first"));
    memory.add(MemoryEntry::assistant("second"));
    memory.add(MemoryEntry::user("third"));

    assert_eq!(memory.len(), 2);
    let entries: Vec<&str> = memory.entries().iter().map(|e| e.content.as_str()).collect();
    assert_eq!(entries, vec!["second", "third"]);
}

/// FR-004: memory tiers — `MemoryEntry::user` / `assistant` / `system`
/// factory methods set the right `MemoryRole`.
#[test]
fn fr_004_memory_entry_factory_methods_set_role() {
    let u = MemoryEntry::user("hi");
    let a = MemoryEntry::assistant("hello");
    let s = MemoryEntry::system("sys");
    assert!(matches!(u.role, MemoryRole::User));
    assert!(matches!(a.role, MemoryRole::Assistant));
    assert!(matches!(s.role, MemoryRole::System));
}

/// FR-004: memory tiers — `InMemoryStore` saves entries and `search`
/// performs substring matching.
#[test]
fn fr_004_in_memory_store_save_and_search() {
    let mut store = InMemoryStore::new();
    store
        .save(&MemoryEntry::user("the quick brown fox"))
        .expect("save should succeed");
    store
        .save(&MemoryEntry::user("lazy dog"))
        .expect("save should succeed");

    let hits = store
        .search("fox", 10)
        .expect("search should succeed");
    assert_eq!(hits.len(), 1);
    assert!(hits[0].content.contains("fox"));

    store.clear().expect("clear should succeed");
    assert!(
        store.search("fox", 10).expect("search after clear").is_empty(),
        "store should be empty after clear"
    );
}

/// FR-004: memory tiers — `LongTermMemory<S>` delegates to the wrapped
/// store and is generic over any `MemoryStore` impl.
#[test]
fn fr_004_long_term_memory_delegates_to_store() {
    let mut ltm: LongTermMemory<InMemoryStore> = LongTermMemory::new(InMemoryStore::new());
    ltm.add(MemoryEntry::user("remember: rust ownership"))
        .expect("add should succeed");

    let results = ltm
        .search("ownership", 5)
        .expect("search should succeed");
    assert_eq!(results.len(), 1);
    assert!(results[0].content.contains("ownership"));
}

/// FR-004: memory tiers — `MemoryEntry` is JSON-serializable round-trip.
#[test]
fn fr_004_memory_entry_serde_roundtrip() {
    let original = MemoryEntry::user("hello").role;
    let entry = MemoryEntry::user("hello");
    let s = serde_json::to_string(&entry).expect("serialize");
    let parsed: MemoryEntry = serde_json::from_str(&s).expect("deserialize");
    assert_eq!(parsed.content, "hello");
    assert!(matches!(parsed.role, MemoryRole::User));
    let _ = original; // keep var alive for readability of the test
}
