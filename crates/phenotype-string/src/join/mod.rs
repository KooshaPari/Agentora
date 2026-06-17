//! String joining utilities
//!
//! Provides efficient string concatenation


/// Join strings with a separator
pub fn join<T: AsRef<str>>(items: &[T], separator: &str) -> String {
    if items.is_empty() {
        return String::new();
    }
    
    let mut result = String::with_capacity(
        items.iter().map(|s| s.as_ref().len()).sum::<usize>()
            + separator.len() * (items.len() - 1)
    );
    
    for (i, item) in items.iter().enumerate() {
        if i > 0 {
            result.push_str(separator);
        }
        result.push_str(item.as_ref());
    }
    
    result
}

/// Join with commas
pub fn comma_join<T: AsRef<str>>(items: &[T]) -> String {
    join(items, ", ")
}

/// Join with newlines
pub fn line_join<T: AsRef<str>>(items: &[T]) -> String {
    join(items, "\n")
}

/// Efficiently build a string from multiple parts
pub fn concat<T: AsRef<str>>(items: &[T]) -> String {
    let mut result = String::with_capacity(items.iter().map(|s| s.as_ref().len()).sum());
    for item in items {
        result.push_str(item.as_ref());
    }
    result
}

/// Builder for efficient string construction
#[derive(Debug, Default)]
pub struct StringBuilder {
    buffer: String,
}

impl StringBuilder {
    /// Create a new builder with specified capacity
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            buffer: String::with_capacity(capacity),
        }
    }
    
    /// Append a string
    pub fn append(&mut self, s: &str) -> &mut Self {
        self.buffer.push_str(s);
        self
    }
    
    /// Get the built string
    pub fn build(self) -> String {
        self.buffer
    }
    
    /// Get current length
    pub fn len(&self) -> usize {
        self.buffer.len()
    }
    
    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.buffer.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_join() {
        assert_eq!(join(&["a", "b", "c"], ", "), "a, b, c");
        assert_eq!(join(&["a"], ", "), "a");
    }

    #[test]
    fn test_comma_join() {
        assert_eq!(comma_join(&["a", "b"]), "a, b");
    }

    #[test]
    fn test_string_builder() {
        let mut builder = StringBuilder::with_capacity(10);
        builder.append("Hello").append(" ").append("World");
        assert_eq!(builder.build(), "Hello World");
    }
}
