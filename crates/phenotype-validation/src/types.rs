//! Common validation types

/// Trait for types that can be validated
pub trait Validatable {
    /// Validation error type
    type Error;

    /// Validate the value
    fn validate(&self) -> Result<(), Self::Error>;
}

/// Range validation for numeric types
#[derive(Debug, Clone)]
pub struct Range<T> {
    min: Option<T>,
    max: Option<T>,
}

impl<T> Range<T> {
    pub fn new() -> Self {
        Self {
            min: None,
            max: None,
        }
    }

    pub fn with_min(mut self, min: T) -> Self {
        self.min = Some(min);
        self
    }

    pub fn with_max(mut self, max: T) -> Self {
        self.max = Some(max);
        self
    }

    /// Check if value is in range
    pub fn contains(&self, value: &T) -> bool
    where
        T: PartialOrd,
    {
        if let Some(min) = &self.min {
            if value < min {
                return false;
            }
        }
        if let Some(max) = &self.max {
            if value > max {
                return false;
            }
        }
        true
    }
}

impl<T> Default for Range<T> {
    fn default() -> Self {
        Self::new()
    }
}
