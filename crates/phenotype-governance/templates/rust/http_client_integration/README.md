# HTTP Client Integration Template

This template shows how to integrate `phenotype-http-client` into your Rust project.

## Features

- ReqwestAdapter for production
- MockAdapter for testing
- Request/response interceptors
- Retry configuration

## Files

- `Cargo.toml` - Dependencies
- `src/api_client.rs` - HTTP client wrapper
- `tests/mock_example.rs` - Testing with MockAdapter

## Quick Start

1. Copy these files to your project
2. Customize `ApiClient` for your API
3. Use `MockAdapter` for unit tests
4. Use `ReqwestAdapter` for production
