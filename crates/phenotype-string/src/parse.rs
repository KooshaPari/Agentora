//! String parsing utilities
//!
//! Provides utilities for parsing strings into various formats.

use std::collections::HashMap;

/// Parse key=value pairs from a string
pub fn parse_key_value(s: &str, delimiter: char) -> HashMap<String, String> {
    let mut result = HashMap::new();
    
    for part in s.split(delimiter) {
        if let Some(pos) = part.find('=') {
            let key = part[..pos].trim().to_string();
            let value = part[pos + 1..].trim().to_string();
            result.insert(key, value);
        }
    }
    
    result
}

/// Parse comma-separated values
pub fn parse_csv(s: &str) -> Vec<String> {
    s.split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

/// Parse a boolean from various string representations
pub fn parse_bool(s: &str) -> Option<bool> {
    match s.trim().to_lowercase().as_str() {
        "true" | "yes" | "1" | "on" => Some(true),
        "false" | "no" | "0" | "off" => Some(false),
        _ => None,
    }
}

/// Extract a value from a JSON-like string (simple key lookup)
pub fn extract_json_value<'a>(json: &'a str, key: &str) -> Option<&'a str> {
    let search = format!("\"{}\":", key);
    if let Some(pos) = json.find(&search) {
        let start = pos + search.len();
        let rest = &json[start..];
        
        // Find the value
        let end = rest.find(&[',', '}'][..]).unwrap_or(rest.len());
        let value = rest[..end].trim();
        
        // Remove quotes if present
        if value.starts_with('"') && value.ends_with('"') {
            return Some(&value[1..value.len() - 1]);
        }
        return Some(value);
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_key_value() {
        let result = parse_key_value("a=1,b=2", ',');
        assert_eq!(result.get("a"), Some(&"1".to_string()));
        assert_eq!(result.get("b"), Some(&"2".to_string()));
    }

    #[test]
    fn test_parse_csv() {
        let result = parse_csv("a, b, c");
        assert_eq!(result, vec!["a", "b", "c"]);
    }

    #[test]
    fn test_parse_bool() {
        assert_eq!(parse_bool("true"), Some(true));
        assert_eq!(parse_bool("FALSE"), Some(false));
        assert_eq!(parse_bool("yes"), Some(true));
        assert_eq!(parse_bool("unknown"), None);
    }
}
