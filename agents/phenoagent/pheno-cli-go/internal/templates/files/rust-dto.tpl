//! DTOs

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CreateEntityDto {
    pub name: String,
    pub description: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct UpdateEntityDto {
    pub name: String,
    pub description: String,
}
