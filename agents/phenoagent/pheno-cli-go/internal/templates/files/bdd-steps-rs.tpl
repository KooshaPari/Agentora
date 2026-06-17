use cucumber::{given, then, when, World};

// World state for BDD tests
#[derive(Debug, World)]
pub struct TestWorld {
    pub entity: Option<Entity>,
    pub last_error: Option<Error>,
    pub events: Vec<Event>,
    pub config: TestConfig,
}

impl TestWorld {
    pub fn new() -> Self {
        Self {
            entity: None,
            last_error: None,
            events: Vec::new(),
            config: TestConfig::default(),
        }
    }
}

#[given(regex = r"^the (.+) system is initialized$")]
async fn system_initialized(world: &mut TestWorld, system: String) {
    world.config = TestConfig::for_system(&system);
}

#[given("a valid entity configuration")]
async fn valid_entity_config(world: &mut TestWorld) {
    world.config = TestConfig::valid();
}

#[given("an invalid entity configuration")]
async fn invalid_entity_config(world: &mut TestWorld) {
    world.config = TestConfig::invalid();
}

#[given(regex = r"^an existing entity in state \"(.+)\"$")]
async fn entity_in_state(world: &mut TestWorld, state: String) {
    world.entity = Some(Entity::with_state(&state));
}

#[given("an unauthenticated user")]
async fn unauthenticated_user(world: &mut TestWorld) {
    world.config.auth_token = None;
}

#[given(regex = r"^(\\d+) concurrent operations$")]
async fn concurrent_operations(world: &mut TestWorld, count: usize) {
    world.config.concurrent_ops = count;
}

#[when("I create a new entity")]
async fn create_entity(world: &mut TestWorld) {
    match create_entity_with_config(&world.config).await {
        Ok(entity) => world.entity = Some(entity),
        Err(e) => world.last_error = Some(e),
    }
}

#[when("I attempt to create a new entity")]
async fn attempt_create_entity(world: &mut TestWorld) {
    match create_entity_with_config(&world.config).await {
        Ok(entity) => world.entity = Some(entity),
        Err(e) => world.last_error = Some(e),
    }
}

#[when(regex = r"^I execute the \"(.+)\" transition$")]
async fn execute_transition(world: &mut TestWorld, transition: String) {
    if let Some(ref mut entity) = world.entity {
        match entity.transition(&transition).await {
            Ok(event) => world.events.push(event),
            Err(e) => world.last_error = Some(e),
        }
    }
}

#[when("I attempt to access protected resources")]
async fn access_protected(world: &mut TestWorld) {
    match access_resources(&world.config).await {
        Ok(_) => (),
        Err(e) => world.last_error = Some(e),
    }
}

#[then("the entity should be persisted")]
async fn entity_persisted(world: &mut TestWorld) {
    assert!(world.entity.is_some(), "Entity should have been created");
    assert!(world.entity.as_ref().unwrap().id.is_some(), "Entity should have an ID");
}

#[then("the entity ID should be returned")]
async fn entity_id_returned(world: &mut TestWorld) {
    assert!(world.entity.as_ref().map(|e| e.id.is_some()).unwrap_or(false), "Entity ID should be present");
}

#[then("the operation should fail")]
async fn operation_failed(world: &mut TestWorld) {
    assert!(world.last_error.is_some(), "Operation should have failed");
}

#[then("an appropriate error should be returned")]
async fn appropriate_error(world: &mut TestWorld) {
    let error = world.last_error.as_ref().expect("Error should exist");
    assert!(error.is_validation() || error.is_domain(), "Error should be validation or domain");
}

#[then(regex = r"^the entity should be in state \"(.+)\"$")]
async fn entity_in_expected_state(world: &mut TestWorld, expected: String) {
    let entity = world.entity.as_ref().expect("Entity should exist");
    assert_eq!(entity.state, expected, "Entity should be in state {}", expected);
}

#[then("the transition event should be recorded")]
async fn transition_recorded(world: &mut TestWorld) {
    assert!(!world.events.is_empty(), "At least one event should be recorded");
}

#[then("the request should be denied")]
async fn request_denied(world: &mut TestWorld) {
    let error = world.last_error.as_ref().expect("Error should exist");
    assert!(error.is_auth(), "Error should be authentication error");
}

#[then("all operations should complete successfully")]
async fn all_operations_success(world: &mut TestWorld) {
    assert!(world.last_error.is_none(), "All operations should succeed");
}

#[then(regex = r"^the average response time should be under (\\d+)ms$")]
async fn response_time_under_threshold(world: &mut TestWorld, threshold: u64) {
    let avg_time = world.events.iter().map(|e| e.duration_ms).sum::<u64>() / world.events.len().max(1) as u64;
    assert!(avg_time < threshold, "Average response time {}ms should be under {}ms", avg_time, threshold);
}

// Helper types
#[derive(Debug, Clone)]
pub struct Entity {
    pub id: Option<String>,
    pub state: String,
}

impl Entity {
    pub fn with_state(state: &str) -> Self {
        Self {
            id: Some(uuid::Uuid::new_v4().to_string()),
            state: state.to_string(),
        }
    }

    pub async fn transition(&mut self, name: &str) -> Result<Event, Error> {
        Ok(Event { name: name.to_string(), duration_ms: 10 })
    }
}

#[derive(Debug, Clone)]
pub struct Event {
    pub name: String,
    pub duration_ms: u64,
}

#[derive(Debug, Clone)]
pub struct Error {
    pub kind: ErrorKind,
    pub message: String,
}

impl Error {
    pub fn is_validation(&self) -> bool {
        matches!(self.kind, ErrorKind::Validation)
    }
    pub fn is_domain(&self) -> bool {
        matches!(self.kind, ErrorKind::Domain)
    }
    pub fn is_auth(&self) -> bool {
        matches!(self.kind, ErrorKind::Auth)
    }
}

#[derive(Debug, Clone)]
pub enum ErrorKind {
    Validation,
    Domain,
    Auth,
    Other,
}

#[derive(Debug, Clone)]
pub struct TestConfig {
    pub auth_token: Option<String>,
    pub concurrent_ops: usize,
    pub timeout: std::time::Duration,
    pub valid: bool,
}

impl TestConfig {
    pub fn default() -> Self {
        Self { auth_token: Some("test-token".to_string()), concurrent_ops: 1, timeout: std::time::Duration::from_secs(30), valid: true }
    }
    pub fn valid() -> Self {
        Self { valid: true, ..Self::default() }
    }
    pub fn invalid() -> Self {
        Self { valid: false, ..Self::default() }
    }
    pub fn for_system(_system: &str) -> Self {
        Self::default()
    }
}

pub async fn create_entity_with_config(config: &TestConfig) -> Result<Entity, Error> {
    if !config.valid {
        return Err(Error { kind: ErrorKind::Validation, message: "Invalid configuration".to_string() });
    }
    Ok(Entity { id: Some(uuid::Uuid::new_v4().to_string()), state: "created".to_string() })
}

pub async fn access_resources(config: &TestConfig) -> Result<(), Error> {
    if config.auth_token.is_none() {
        return Err(Error { kind: ErrorKind::Auth, message: "Unauthorized".to_string() });
    }
    Ok(())
}
