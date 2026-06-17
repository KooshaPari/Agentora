//! Domain entities

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Entity {
    pub id: Uuid,
    pub name: String,
    pub description: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Entity {
    pub fn new(name: impl Into<String>, description: impl Into<String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            name: name.into(),
            description: description.into(),
            created_at: now,
            updated_at: now,
        }
    }

    pub fn update(&mut self, name: impl Into<String>, description: impl Into<String>) {
        self.name = name.into();
        self.description = description.into();
        self.updated_at = Utc::now();
    }
}
