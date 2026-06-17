//! String sanitization utilities
//!
//! Provides string cleaning and safety utilities

/// Sanitize a string for safe display (removes control characters)
pub fn sanitize(s: &str) -> String {
    s.chars()
        .filter(|c| !c.is_control() || *c == '\n' || *c == '\t')
        .collect()
}

/// Escape special regex characters
pub fn escape_regex(s: &str) -> String {
    regex::escape(s)
}

/// Remove all whitespace
pub fn remove_whitespace(s: &str) -> String {
    s.chars().filter(|c| !c.is_whitespace()).collect()
}

/// Normalize whitespace (multiple spaces become single)
pub fn normalize_whitespace(s: &str) -> String {
    let mut result = String::with_capacity(s.len());
    let mut prev_whitespace = false;
    
    for c in s.chars() {
        if c.is_whitespace() {
            if !prev_whitespace {
                result.push(' ');
                prev_whitespace = true;
            }
        } else {
            result.push(c);
            prev_whitespace = false;
        }
    }
    
    result.trim().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize() {
        assert_eq!(sanitize("Hello\x00World"), "HelloWorld");
    }

    #[test]
    fn test_remove_whitespace() {
        assert_eq!(remove_whitespace("a b c"), "abc");
    }

    #[test]
    fn test_normalize_whitespace() {
        assert_eq!(normalize_whitespace("a   b    c"), "a b c");
    }
}
