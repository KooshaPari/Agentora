//! String compression utilities
//!
//! Provides compression for string data using zstd.

use std::io::{self, Read, Write};
use zstd::stream::{read, write};

/// Compression errors
#[derive(Debug, thiserror::Error)]
pub enum CompressionError {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),
    
    #[error("Zstd error: {0}")]
    Zstd(String),
}

/// Compress string data using zstd
pub fn compress(data: &str, level: i32) -> Result<Vec<u8>, CompressionError> {
    let mut encoder = write::Encoder::new(Vec::new(), level)?;
    encoder.write_all(data.as_bytes())?;
    let compressed = encoder.finish()?;
    Ok(compressed)
}

/// Decompress data to string
pub fn decompress(data: &[u8]) -> Result<String, CompressionError> {
    let mut decoder = read::Decoder::new(data)?;
    let mut result = String::new();
    decoder.read_to_string(&mut result)?;
    Ok(result)
}

/// Estimate compression ratio
pub fn compression_ratio(original: &str, compressed: &[u8]) -> f64 {
    if original.is_empty() {
        return 1.0;
    }
    original.len() as f64 / compressed.len() as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_roundtrip() {
        let original = "Hello, World! This is a test string for compression.";
        let compressed = compress(original, 3).unwrap();
        let decompressed = decompress(&compressed).unwrap();
        assert_eq!(decompressed, original);
    }
}
