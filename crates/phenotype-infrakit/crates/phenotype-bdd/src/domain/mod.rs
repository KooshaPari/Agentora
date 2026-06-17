//! Domain layer for BDD functionality

pub mod entities;
pub mod ports;
pub mod services;

pub type DomainError = crate::BddError;
