//! String normalization utilities
//!
//! Provides Unicode normalization and text cleaning.

use unicode_normalization::UnicodeNormalization;

/// Normalize string to NFC (Canonical Decomposition followed by Canonical Composition)
pub fn normalize_nfc(s: &str) -> String {
    s.nfc().collect()
}

/// Normalize string to NFD (Canonical Decomposition)
pub fn normalize_nfd(s: &str) -> String {
    s.nfd().collect()
}

/// Normalize string to NFKC (Compatibility Decomposition followed by Canonical Composition)
pub fn normalize_nfkc(s: &str) -> String {
    s.nfkc().collect()
}

/// Remove diacritics from characters (e.g., "café" -> "cafe")
pub fn remove_diacritics(s: &str) -> String {
    s.nfd()
        .filter(|c| !matches!(c, '\u{0300}'..='\u{036F}'))
        .collect::<String>()
        .nfc()
        .collect()
}

/// Convert to ASCII, replacing non-ASCII characters
pub fn to_ascii_lossy(s: &str) -> String {
    s.chars()
        .map(|c| {
            if c.is_ascii() {
                c
            } else {
                // Simple ASCII approximation
                match c {
                    'é' | 'è' | 'ê' | 'ë' => 'e',
                    'á' | 'à' | 'â' | 'ä' => 'a',
                    'í' | 'ì' | 'î' | 'ï' => 'i',
                    'ó' | 'ò' | 'ô' | 'ö' => 'o',
                    'ú' | 'ù' | 'û' | 'ü' => 'u',
                    'ñ' => 'n',
                    'ç' => 'c',
                    _ => '?',
                }
            }
        })
        .collect()
}

/// Normalize whitespace and line endings
pub fn normalize_whitespace(s: &str) -> String {
    s.lines()
        .map(|line| line.trim())
        .filter(|line| !line.is_empty())
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_nfc_normalization() {
        let s = "caf\u{0065}\u{0301}"; // "café" using combining e + acute
        assert_eq!(normalize_nfc(s), "café");
    }

    #[test]
    fn test_remove_diacritics() {
        assert_eq!(remove_diacritics("café"), "cafe");
    }

    #[test]
    fn test_to_ascii_lossy() {
        assert_eq!(to_ascii_lossy("café"), "cafe");
    }
}
