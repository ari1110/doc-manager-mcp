// Test fixture: Rust struct with serde derives.
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub name: String,
    #[serde(default)]
    pub version: Option<String>,
    pub debug: bool,
    #[serde(rename = "max_retries")]
    pub max_retries: u32,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DatabaseConfig {
    pub host: String,
    pub port: u16,
    pub database: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub username: Option<String>,
}
