# Integration Guide

This guide shows how to integrate the three new shared crates into your projects.

## Table of Contents

1. [Adding BDD Tests](#adding-bdd-tests)
2. [Using the HTTP Client](#using-the-http-client)
3. [Adding Validation](#adding-validation)
4. [Complete Example](#complete-example)

---

## Adding BDD Tests

### 1. Add Dependency

```toml
[dev-dependencies]
phenotype-bdd = { path = "../phenotype-infrakit/crates/phenotype-bdd" }
tokio = { version = "1", features = ["full"] }
```

### 2. Create Feature File

Create `tests/features/my_feature.feature`:

```gherkin
Feature: My Feature
  Scenario: Something happens
    Given some precondition
    When I do something
    Then something should happen
```

### 3. Create Step Definitions

Create `tests/steps/mod.rs`:

```rust
use phenotype_bdd::{StepRegistry, StepContext, StepArgs, Result};

pub async fn setup_registry() -> Result<StepRegistry> {
    let mut registry = StepRegistry::new();
    
    registry.given("some precondition", |ctx: &mut StepContext, _args: StepArgs| async move {
        ctx.insert("ready", true)?;
        Ok(())
    }).await?;
    
    registry.when("I do something", |ctx: &mut StepContext, _args: StepArgs| async move {
        ctx.insert("done", true)?;
        Ok(())
    }).await?;
    
    registry.then("something should happen", |ctx: &mut StepContext, _args: StepArgs| async move {
        let ready: bool = ctx.get("ready")?.unwrap_or(false);
        let done: bool = ctx.get("done")?.unwrap_or(false);
        assert!(ready && done, "Precondition and action not completed");
        Ok(())
    }).await?;
    
    Ok(registry)
}
```

### 4. Write Test

```rust
#[tokio::test]
async fn test_my_feature() -> Result<()> {
    let feature = FeatureParser::parse_file("tests/features/my_feature.feature").await?;
    let registry = setup_registry().await?;
    let runner = Runner::new(registry);
    let result = runner.run(feature).await?;
    
    assert_eq!(result.failed, 0, "Some scenarios failed");
    Ok(())
}
```

---

## Using the HTTP Client

### 1. Add Dependency

```toml
[dependencies]
phenotype-http-client = { path = "../phenotype-infrakit/crates/phenotype-http-client" }
```

### 2. Use ReqwestAdapter (Production)

```rust
use phenotype_http_client::{ReqwestAdapter, HttpClientPort, Request, Method};

async fn fetch_data() -> Result<(), Box<dyn std::error::Error>> {
    let client = ReqwestAdapter::new();
    
    // GET request
    let response = client.get("https://api.example.com/data").await?;
    
    if response.is_success() {
        let data: serde_json::Value = response.json()?;
        println!("Received: {:?}", data);
    }
    
    // POST request with body
    let request = Request::builder()
        .method(Method::POST)
        .uri("https://api.example.com/users")
        .header("Content-Type", "application/json")
        .body(r#"{"name": "John"}"#.as_bytes())
        .build()?;
    
    let response = client.execute(request).await?;
    println!("Created user with status: {}", response.status);
    
    Ok(())
}
```

### 3. Use MockAdapter (Testing)

```rust
use phenotype_http_client::MockAdapter;

#[tokio::test]
async fn test_api_call() {
    let mock = MockAdapter::new();
    
    // Configure mock response
    mock.when("https://api.example.com/users")
        .then_return_json(&serde_json::json!({
            "id": 1,
            "name": "Test User"
        })).unwrap();
    
    // Make request
    let response = mock.get("https://api.example.com/users").await.unwrap();
    
    // Verify
    assert!(response.is_success());
    assert!(mock.was_requested("https://api.example.com/users"));
}
```

---

## Adding Validation

### 1. Add Dependency

```toml
[dependencies]
phenotype-validation = { path = "../phenotype-infrakit/crates/phenotype-validation" }
```

### 2. Create Validator

```rust
use phenotype_validation::{Validator, Result};
use serde_json::json;

fn validate_user_data() -> Result<()> {
    let validator = Validator::new()
        .required("name")
        .string("email")
        .email()
        .integer("age")
        .min(0.0)
        .max(150.0);
    
    let data = json!({
        "name": "John",
        "email": "john@example.com",
        "age": 30
    });
    
    let result = validator.validate(&data)?;
    
    if !result.is_valid {
        for error in result.errors {
            println!("Validation error: {}", error);
        }
        return Err(error.into());
    }
    
    Ok(())
}
```

### 3. Validate Configuration

```rust
use phenotype_validation::Validator;
use serde::Deserialize;

#[derive(Deserialize)]
struct Config {
    name: String,
    version: String,
    timeout: u64,
}

fn validate_config(config: &Config) -> Result<(), Box<dyn std::error::Error>> {
    let validator = Validator::new()
        .required("name")
        .required("version")
        .integer("timeout")
        .min(1.0)
        .max(300.0);
    
    let config_json = serde_json::to_value(config)?;
    let result = validator.validate(&config_json)?;
    
    if !result.is_valid {
        return Err(format!("Config validation failed: {:?}", result.errors).into());
    }
    
    Ok(())
}
```

---

## Complete Example

Here's a complete example showing all three crates working together:

```rust
// Cargo.toml
[dependencies]
phenotype-bdd = { path = "../phenotype-infrakit/crates/phenotype-bdd" }
phenotype-http-client = { path = "../phenotype-infrakit/crates/phenotype-http-client" }
phenotype-validation = { path = "../phenotype-infrakit/crates/phenotype-validation" }
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"

// tests/features/api_integration.feature
Feature: API Integration
  Background:
    Given the API client is configured
    And the API endpoint is "https://api.example.com"
  
  Scenario: Create and validate user
    Given I have user data:
      """json
      {"name": "John", "email": "john@example.com", "age": 30}
      """
    And the data passes validation
    When I POST to "/users"
    Then the response status should be 201
    And the response should contain valid user data

// src/api_client.rs
use phenotype_http_client::{ReqwestAdapter, HttpClientPort, Request, Method};
use phenotype_validation::{Validator, Result as ValidationResult};
use serde_json::json;

pub struct ApiClient {
    http: ReqwestAdapter,
    validator: Validator,
}

impl ApiClient {
    pub fn new() -> Self {
        let validator = Validator::new()
            .required("name")
            .email("email")
            .integer("age")
            .min(0.0)
            .max(150.0);
        
        Self {
            http: ReqwestAdapter::new(),
            validator,
        }
    }
    
    pub async fn create_user(&self, user_data: &serde_json::Value) -> Result<User, Error> {
        // Validate first
        let validation = self.validator.validate(user_data)?;
        if !validation.is_valid {
            return Err(Error::Validation(validation.errors));
        }
        
        // Then send HTTP request
        let request = Request::builder()
            .method(Method::POST)
            .uri("https://api.example.com/users")
            .header("Content-Type", "application/json")
            .body(user_data.to_string().as_bytes())
            .build()?;
        
        let response = self.http.execute(request).await?;
        
        if response.is_success() {
            let user: User = response.json()?;
            Ok(user)
        } else {
            Err(Error::Http(response.status))
        }
    }
}

// tests/integration_test.rs
use phenotype_bdd::{FeatureParser, StepRegistry, Runner, StepContext, StepArgs, Result};

#[tokio::test]
async fn test_api_integration() -> Result<()> {
    let feature = FeatureParser::parse_file("tests/features/api_integration.feature").await?;
    let registry = setup_api_steps().await?;
    let runner = Runner::new(registry);
    let result = runner.run(feature).await?;
    
    assert_eq!(result.failed, 0);
    Ok(())
}

async fn setup_api_steps() -> Result<StepRegistry> {
    let mut registry = StepRegistry::new();
    
    // Given the API client is configured
    registry.given("the API client is configured", |ctx, _| async move {
        ctx.insert("client", ApiClient::new())?;
        Ok(())
    }).await?;
    
    // And the data passes validation
    registry.given("the data passes validation", |ctx, _| async move {
        // Validation happens in the client
        Ok(())
    }).await?;
    
    // When I POST to "/users"
    registry.when(r#"I POST to "([^"]+)""#, |ctx, args| async move {
        let path = args.get(0).unwrap();
        let client: ApiClient = ctx.get("client")?.unwrap();
        let data = ctx.get("user_data")?.unwrap();
        
        let response = client.create_user(&data).await;
        ctx.insert("response", response)?;
        Ok(())
    }).await?;
    
    Ok(registry)
}
```

---

## Migration Checklist

When integrating into existing projects:

- [ ] Add crate dependencies to Cargo.toml
- [ ] Create `tests/features/` directory for .feature files
- [ ] Create `tests/steps/` directory for step definitions
- [ ] Replace direct reqwest usage with phenotype-http-client
- [ ] Add validation for all configuration structures
- [ ] Write at least one BDD feature file for core functionality
- [ ] Add step registry setup function
- [ ] Write integration test using Runner
- [ ] Update documentation
- [ ] Update CI to run BDD tests
