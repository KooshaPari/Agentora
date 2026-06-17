//! # Canonical Port Traits (DEPRECATED)
//!
//! This crate is deprecated. Use `phenotype-port-traits` directly.
//!
//! ```toml
//! [dependencies]
//! phenotype-port-traits = "0.2"
//! ```
//!
//! ## Migration
//!
//! Replace `phenotype-ports-canonical` with `phenotype-port-traits` in your Cargo.toml.

#![deprecated(
    since = "0.2.0",
    note = "Use phenotype-port-traits directly instead"
)]

pub use phenotype_port_traits::inbound;
pub use phenotype_port_traits::outbound;
