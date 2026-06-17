//! Test fixtures for Phenotype

/// Fixture trait
pub trait Fixture<T>: Clone {
    /// Create a fixture
    fn create() -> T;
}

/// Test data fixture
#[derive(Debug, Clone)]
pub struct TestData;

impl Fixture<TestData> for TestData {
    fn create() -> TestData {
        TestData
    }
}

/// Fixture that can be reset
pub trait Resettable {
    /// Reset to initial state
    fn reset(&mut self);
}

/// Temporary file fixture
#[derive(Debug)]
pub struct TempFile {
    path: std::path::PathBuf,
}

impl TempFile {
    /// Create a new temp file
    pub fn new() -> Self {
        let path = std::env::temp_dir().join(format!("test_{}", uuid::Uuid::new_v4()));
        Self { path }
    }
    
    /// Get file path
    pub fn path(&self) -> &std::path::Path {
        &self.path
    }
}

impl Drop for TempFile {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}
