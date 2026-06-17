//! Mock testing utilities for Phenotype
//!
//! Provides mocking capabilities for unit tests.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Type alias for mock function handler
type MockHandler<I, O> = Arc<Mutex<Box<dyn FnMut(I) -> O + Send + 'static>>>;

/// A mock function call record
#[derive(Debug, Clone)]
pub struct Call {
    pub name: String,
    pub args: Vec<String>,
}

/// Mock context for tracking calls
#[derive(Debug, Default)]
pub struct MockContext {
    calls: Arc<Mutex<Vec<Call>>>,
}

impl MockContext {
    /// Create a new mock context
    pub fn new() -> Self {
        Self {
            calls: Arc::new(Mutex::new(Vec::new())),
        }
    }
    
    /// Record a function call
    pub fn record_call(&self, name: impl Into<String>, args: Vec<String>) {
        let mut calls = self.calls.lock().unwrap();
        calls.push(Call {
            name: name.into(),
            args,
        });
    }
    
    /// Get all recorded calls
    pub fn calls(&self) -> Vec<Call> {
        self.calls.lock().unwrap().clone()
    }
    
    /// Check if a function was called
    pub fn was_called(&self, name: &str) -> bool {
        self.calls.lock().unwrap().iter().any(|c| c.name == name)
    }
    
    /// Get call count for a function
    pub fn call_count(&self, name: &str) -> usize {
        self.calls.lock().unwrap().iter().filter(|c| c.name == name).count()
    }
    
    /// Reset all recorded calls
    pub fn reset(&self) {
        self.calls.lock().unwrap().clear();
    }
}

/// A generic mock that returns predefined values
pub struct Mock<T, R> {
    returns: Arc<Mutex<HashMap<T, R>>>,
    default: Arc<Mutex<Option<R>>>,
    context: MockContext,
}

impl<T: std::hash::Hash + Eq + Clone + std::fmt::Debug, R: Clone> Mock<T, R> {
    /// Create a new mock
    pub fn new() -> Self {
        Self {
            returns: Arc::new(Mutex::new(HashMap::new())),
            default: Arc::new(Mutex::new(None)),
            context: MockContext::new(),
        }
    }
    
    /// Set return value for a specific input
    pub fn when(&self, input: T, output: R) -> &Self {
        self.returns.lock().unwrap().insert(input, output);
        self
    }
    
    /// Set default return value
    pub fn default_return(&self, output: R) -> &Self {
        *self.default.lock().unwrap() = Some(output);
        self
    }
    
    /// Call the mock function
    pub fn call(&self, input: T) -> R {
        let returns = self.returns.lock().unwrap();
        let result = returns.get(&input).cloned().or_else(|| {
            self.default.lock().unwrap().clone()
        });
        
        drop(returns);
        
        self.context.record_call(
            "mock",
            vec![format!("{:?}", input)]
        );
        
        result.expect("No return value set for mock")
    }
    
    /// Get the mock context
    pub fn context(&self) -> &MockContext {
        &self.context
    }
}

impl<T: std::hash::Hash + Eq + Clone + std::fmt::Debug, R: Clone> Default for Mock<T, R> {
    fn default() -> Self {
        Self::new()
    }
}

/// A mock for functions with side effects
pub struct MockFn<I, O> {
    handler: MockHandler<I, O>,
    context: MockContext,
}

impl<I, O> MockFn<I, O> {
    /// Create a new mock function
    pub fn new<F>(handler: F) -> Self
    where
        F: FnMut(I) -> O + Send + 'static,
    {
        Self {
            handler: Arc::new(Mutex::new(Box::new(handler))),
            context: MockContext::new(),
        }
    }
    
    /// Call the mock function
    pub fn call(&self, input: I) -> O {
        let mut handler = self.handler.lock().unwrap();
        handler(input)
    }
    
    /// Get the mock context
    pub fn context(&self) -> &MockContext {
        &self.context
    }
}

/// Macro for creating simple mocks
#[macro_export]
macro_rules! mock_fn {
    ($name:ident, $input:ty, $output:ty, $body:expr) => {
        fn $name() -> $crate::MockFn<$input, $output> {
            $crate::MockFn::new($body)
        }
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mock_context() {
        let ctx = MockContext::new();
        ctx.record_call("test", vec!["arg1".to_string()]);
        assert!(ctx.was_called("test"));
        assert_eq!(ctx.call_count("test"), 1);
    }

    #[test]
    fn test_mock() {
        let mock: Mock<String, i32> = Mock::new();
        mock.when("hello".to_string(), 42)
            .default_return(0);
        
        assert_eq!(mock.call("hello".to_string()), 42);
        assert_eq!(mock.call("world".to_string()), 0);
    }

    #[test]
    fn test_mock_fn() {
        let mock = MockFn::new(|x: i32| x * 2);
        assert_eq!(mock.call(5), 10);
    }
}
