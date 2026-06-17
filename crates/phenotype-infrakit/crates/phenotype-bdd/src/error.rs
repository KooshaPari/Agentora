use thiserror::Error;

#[derive(Error, Debug)]
pub enum BddError {
    #[error("step failed: {message}")]
    StepFailed { message: String },
    #[error("no matching step definition for: {text}")]
    NoMatch { text: String },
    #[error("ambiguous step match: {text}")]
    AmbiguousMatch { text: String },
    #[error("parse error: {0}")]
    ParseError(String),
    #[error("io error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("{0}")]
    Other(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-BDD-010 - BddError variants
    #[test]
    fn test_step_failed_error() {
        let err = BddError::StepFailed {
            message: "assertion failed".into(),
        };
        assert_eq!(err.to_string(), "step failed: assertion failed");
    }

    // Traces to: FR-BDD-011 - NoMatch error
    #[test]
    fn test_no_match_error() {
        let err = BddError::NoMatch {
            text: "I click button".into(),
        };
        assert_eq!(
            err.to_string(),
            "no matching step definition for: I click button"
        );
    }

    // Traces to: FR-BDD-012 - AmbiguousMatch error
    #[test]
    fn test_ambiguous_match_error() {
        let err = BddError::AmbiguousMatch {
            text: "I see the page".into(),
        };
        assert!(err.to_string().contains("ambiguous"));
    }

    // Traces to: FR-BDD-013 - ParseError
    #[test]
    fn test_parse_error() {
        let err = BddError::ParseError("invalid syntax".into());
        assert_eq!(err.to_string(), "parse error: invalid syntax");
    }

    // Traces to: FR-BDD-014 - IoError conversion
    #[test]
    fn test_io_error_conversion() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let err: BddError = io_err.into();
        assert!(matches!(err, BddError::IoError(_)));
    }

    // Traces to: FR-BDD-015 - Generic Other error
    #[test]
    fn test_other_error() {
        let err = BddError::Other("something went wrong".into());
        assert_eq!(err.to_string(), "something went wrong");
    }
}
