//! Test infrastructure for Phenotype
//!
//! Provides test runners, fixtures, and test utilities.

pub mod fixtures;
pub mod runner;

/// Test result
#[derive(Debug, Clone)]
pub struct TestResult {
    pub name: String,
    pub passed: bool,
    pub duration_ms: u64,
    pub message: Option<String>,
}

/// Test case trait
pub trait TestCase: Send + Sync {
    /// Run the test
    fn run(&self) -> TestResult;
    
    /// Get test name
    fn name(&self) -> &str;
}

/// Test suite
#[derive(Debug, Default)]
pub struct TestSuite {
    name: String,
    tests: Vec<Box<dyn TestCase>>,
}

impl TestSuite {
    /// Create a new test suite
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            tests: Vec::new(),
        }
    }
    
    /// Add a test case
    pub fn add_test(&mut self, test: Box<dyn TestCase>) {
        self.tests.push(test);
    }
    
    /// Run all tests
    pub fn run(&self) -> Vec<TestResult> {
        self.tests.iter().map(|t| t.run()).collect()
    }
    
    /// Get test count
    pub fn count(&self) -> usize {
        self.tests.len()
    }
    
    /// Get suite name
    pub fn name(&self) -> &str {
        &self.name
    }
}

/// Test reporter
pub trait TestReporter: Send + Sync {
    /// Report a test result
    fn report(&self, result: &TestResult);
    
    /// Report summary
    fn summary(&self, passed: usize, failed: usize, duration_ms: u64);
}

/// Console test reporter
#[derive(Debug)]
pub struct ConsoleReporter;

impl ConsoleReporter {
    /// Create a new console reporter
    pub fn new() -> Self {
        Self
    }
}

impl Default for ConsoleReporter {
    fn default() -> Self {
        Self::new()
    }
}

impl TestReporter for ConsoleReporter {
    fn report(&self, result: &TestResult) {
        let status = if result.passed { "PASS" } else { "FAIL" };
        println!("[{}] {} ({}ms)", status, result.name, result.duration_ms);
        if let Some(ref msg) = result.message {
            println!("  {}", msg);
        }
    }
    
    fn summary(&self, passed: usize, failed: usize, duration_ms: u64) {
        println!("\n========================================");
        println!("Tests: {} passed, {} failed", passed, failed);
        println!("Duration: {}ms", duration_ms);
        println!("========================================");
    }
}

/// Test harness
pub struct TestHarness {
    suites: Vec<TestSuite>,
    reporter: Box<dyn TestReporter>,
}

impl TestHarness {
    /// Create a new test harness
    pub fn new(reporter: Box<dyn TestReporter>) -> Self {
        Self {
            suites: Vec::new(),
            reporter,
        }
    }
    
    /// Add a test suite
    pub fn add_suite(&mut self, suite: TestSuite) {
        self.suites.push(suite);
    }
    
    /// Run all test suites
    pub fn run(&self) -> bool {
        let start = std::time::Instant::now();
        let mut total_passed = 0;
        let mut total_failed = 0;
        
        for suite in &self.suites {
            println!("\nRunning suite: {}", suite.name());
            let results = suite.run();
            
            for result in &results {
                self.reporter.report(result);
                if result.passed {
                    total_passed += 1;
                } else {
                    total_failed += 1;
                }
            }
        }
        
        let duration = start.elapsed().as_millis() as u64;
        self.reporter.summary(total_passed, total_failed, duration);
        
        total_failed == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct DummyTest {
        name: String,
    }

    impl TestCase for DummyTest {
        fn run(&self) -> TestResult {
            TestResult {
                name: self.name.clone(),
                passed: true,
                duration_ms: 0,
                message: None,
            }
        }
        
        fn name(&self) -> &str {
            &self.name
        }
    }

    #[test]
    fn test_suite() {
        let mut suite = TestSuite::new("test");
        suite.add_test(Box::new(DummyTest { name: "t1".to_string() }));
        assert_eq!(suite.count(), 1);
    }
}
