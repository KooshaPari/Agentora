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
