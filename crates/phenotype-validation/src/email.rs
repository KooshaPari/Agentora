//! Email validation

use regex::Regex;

/// Email validation error
#[derive(Debug, thiserror::Error)]
pub enum EmailValidationError {
    #[error("Invalid email format")]
    InvalidFormat,
    #[error("Email exceeds maximum length")]
    TooLong,
    #[error("Missing @ symbol")]
    MissingAt,
    #[error("Missing domain")]
    MissingDomain,
}

/// Validate an email address
pub fn validate_email(email: &str) -> Result<(), EmailValidationError> {
    if email.len() > 254 {
        return Err(EmailValidationError::TooLong);
    }

    if !email.contains('@') {
        return Err(EmailValidationError::MissingAt);
    }

    let parts: Vec<&str> = email.split('@').collect();
    if parts.len() != 2 || parts[1].is_empty() {
        return Err(EmailValidationError::MissingDomain);
    }

    // Basic regex check
    static EMAIL_REGEX: once_cell::sync::Lazy<Regex> = once_cell::sync::Lazy::new(|| {
        Regex::new(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").unwrap()
    });

    if !EMAIL_REGEX.is_match(email) {
        return Err(EmailValidationError::InvalidFormat);
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_email() {
        assert!(validate_email("test@example.com").is_ok());
    }

    #[test]
    fn test_invalid_email_no_at() {
        assert!(matches!(
            validate_email("invalid.email"),
            Err(EmailValidationError::MissingAt)
        ));
    }
}
