//! String utilities for Phenotype
//!
//! Provides string manipulation, compression, normalization, and parsing utilities.

use thiserror::Error;

pub mod compression;
pub mod join;
pub mod normalization;
pub mod parse;
pub mod sanitize;

/// String utility errors
#[derive(Debug, Error)]
pub enum Error {
    /// Invalid string operation
    #[error("Invalid: {0}")]
    Invalid(String),
    /// Compression error
    #[error("Compression error: {0}")]
    Compression(String),
    /// Decompression error
    #[error("Decompression error: {0}")]
    Decompression(String),
    /// Normalization error
    #[error("Normalization error: {0}")]
    Normalization(String),
    /// Parse error
    #[error("Parse error: {0}")]
    Parse(String),
}

/// Result type for string operations
pub type Result<T> = std::result::Result<T, Error>;

/// Truncate a string to a maximum length with ellipsis
///
/// # Examples
///
/// ```
/// use phenotype_string::truncate;
///
/// let s = "Hello, World!";
/// assert_eq!(truncate(s, 5), "He...");
/// ```
pub fn truncate(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        s.to_string()
    } else if max_len <= 3 {
        s[..max_len].to_string()
    } else {
        format!("{}...", &s[..max_len - 3])
    }
}

/// Reverse a string (handles Unicode correctly)
pub fn reverse(s: &str) -> String {
    s.chars().rev().collect()
}

/// Count characters (not bytes) in a string
pub fn char_count(s: &str) -> usize {
    s.chars().count()
}

/// Check if string is empty or whitespace only
pub fn is_blank(s: &str) -> bool {
    s.trim().is_empty()
}

/// Split string into words
pub fn words(s: &str) -> Vec<&str> {
    s.split_whitespace().collect()
}

/// Convert to snake_case
pub fn to_snake_case(s: &str) -> String {
    let mut result = String::new();
    let mut prev_lower = false;
    
    for c in s.chars() {
        if c.is_uppercase() {
            if prev_lower {
                result.push('_');
            }
            result.push(c.to_lowercase().next().unwrap_or(c));
            prev_lower = false;
        } else if c.is_alphanumeric() {
            result.push(c);
            prev_lower = c.is_lowercase();
        } else {
            result.push('_');
            prev_lower = false;
        }
    }
    
    result.trim_matches('_').to_string()
}

/// Convert to camelCase
pub fn to_camel_case(s: &str) -> String {
    let mut result = String::new();
    let mut capitalize_next = false;
    
    for c in s.chars() {
        if c.is_alphanumeric() {
            if capitalize_next {
                result.push(c.to_uppercase().next().unwrap_or(c));
                capitalize_next = false;
            } else {
                result.push(c.to_lowercase().next().unwrap_or(c));
            }
        } else {
            capitalize_next = true;
        }
    }
    
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_truncate() {
        assert_eq!(truncate("Hello", 10), "Hello");
        assert_eq!(truncate("Hello, World!", 8), "Hello...");
        assert_eq!(truncate("Hi", 2), "Hi");
    }

    #[test]
    fn test_reverse() {
        assert_eq!(reverse("Hello"), "olleH");
        assert_eq!(reverse("123"), "321");
    }

    #[test]
    fn test_char_count() {
        assert_eq!(char_count("Hello"), 5);
        assert_eq!(char_count(""), 0);
    }

    #[test]
    fn test_is_blank() {
        assert!(is_blank(""));
        assert!(is_blank("   "));
        assert!(!is_blank("Hello"));
    }

    #[test]
    fn test_words() {
        assert_eq!(words("Hello World"), vec!["Hello", "World"]);
        assert_eq!(words("one  two"), vec!["one", "two"]);
    }

    #[test]
    fn test_snake_case() {
        assert_eq!(to_snake_case("HelloWorld"), "hello_world");
        assert_eq!(to_snake_case("hello-world"), "hello_world");
    }

    #[test]
    fn test_camel_case() {
        assert_eq!(to_camel_case("hello_world"), "helloWorld");
        assert_eq!(to_camel_case("hello-world"), "helloWorld");
    }
}
