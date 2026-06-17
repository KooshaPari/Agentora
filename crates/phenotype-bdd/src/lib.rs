//! BDD Testing Utilities
//!
//! Provides given-when-then style testing for Phenotype projects.

pub mod given;
pub mod then;
pub mod when;

pub use given::Given;
pub use then::Then;
pub use when::When;

pub mod prelude {
    pub use crate::{Given, Then, When};
}
